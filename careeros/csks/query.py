from __future__ import annotations

import json
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Literal

from careeros.knowledge import GraphEdge, GraphNode, KnowledgeGraph

from .grammar import classify
from .models import (
    CSKSEvidence,
    Citation,
    EvidencePack,
    StructuredQueryResult,
    CSKSAnswer,
    QueryType,
    make_entity_id,
)
from .synthesis import is_synthesis_enabled


@dataclass(frozen=True)
class QueryResult:
    """Internal query result with traversal details."""

    answer: str
    citations: list[dict]
    matched_entities: list[str]
    traversal_path: list[str]
    confidence: float
    entities_found: int
    query_type: str


class CSKSQueryEngine:
    """Query engine for the CareerOS Self-Knowledge System.

    Operates on a KnowledgeGraph populated with CSKS entities.
    Provides deterministic graph traversal, filtering, and path finding.
    """

    _STOPWORDS = frozenset({
        "what", "whats", "why", "where", "when", "which", "who", "whom",
        "how", "does", "do", "can", "could", "would", "should", "is", "are",
        "was", "were", "be", "the", "and", "or", "of", "in", "on", "at",
        "for", "with", "about", "into", "over", "all", "any", "that",
    })

    _DEFINITION_PREFIXES = (" is a", " is an", " is the")
    _GOAL_PREFIXES = (" addresses", " provides", " supports", " aims")

    def __init__(
        self,
        graph: "KnowledgeGraph",
        repo_root: "Path | None" = None,
        profile: dict[str, Any] | None = None,
        synthesis_provider: "AIProvider | None" = None,
    ) -> None:
        self.graph = graph
        self.repo_root = repo_root
        self.profile = profile
        self.synthesis_provider = synthesis_provider
        self._node_cache: dict[str, "GraphNode"] = {}
        self._edge_index: dict[str, list] = defaultdict(list)
        self._reverse_edge_index: dict[str, list] = defaultdict(list)
        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup indices for fast querying."""
        for node_id, node in self.graph.nodes.items():
            self._node_cache[node.id] = node

        for edge in self.graph.edges:
            self._edge_index[edge.source_id].append(edge)
            self._reverse_edge_index[edge.target_id].append(edge)

    def _extract_terms(self, question: str) -> list[str]:
        """Extract candidate entity terms from a question.

        Prefers quoted strings, then CamelCase identifiers, then capitalized
        phrases. Stopwords and pure-numeric tokens are removed. Longer terms
        come first so the most specific match wins.
        """
        import re

        quoted = re.findall(r'"([^"]+)"', question)
        candidates = list(quoted)

        # CamelCase identifiers with optional trailing acronym (e.g. InterviewEngine,
        # ProfileLoader, CareerOS, ResolutionEngine)
        candidates += re.findall(r'\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+|[A-Z]{2,})*\b', question)

        # Acronym + number identifiers (e.g. ADR-008, ADR 008, ADR008)
        candidates += re.findall(r'\b[A-Z]{2,}[- ]?\d+\b', question)

        # Capitalized multi-word phrases
        candidates += re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', question)

        seen = set()
        terms = []
        for term in candidates:
            stripped = term.strip()
            if not stripped:
                continue
            if stripped.lower() in self._STOPWORDS:
                continue
            if stripped.isdigit():
                continue
            key = stripped.lower()
            if key in seen:
                continue
            seen.add(key)
            terms.append(stripped)

        # Most specific (longest) first
        terms.sort(key=lambda t: len(t), reverse=True)
        return terms

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        """Normalize an identifier to a canonical dotted form.

        Equivalent separators (``-``, spaces, ``.``) collapse to ``.`` and a
        separator is inserted between letters and digits, so ``ADR-008``,
        ``adr 008``, ``ADR008`` and ``adr.008`` all normalize to ``adr.008``.
        """
        import re

        normalized = value.lower().replace("-", ".").replace(" ", ".")
        return re.sub(r"([a-z])(\d)", r"\1.\2", normalized)

    def _resolve_target(self, question: str, preferred_types: tuple[str, ...] | None = None) -> "GraphNode | None":
        """Find the best-matching entity node for a question.

        Milestone identifiers (``M1.22``) resolve via tag-prefix match so the
        result is deterministic regardless of graph node ordering. Otherwise
        exact label matches win, then exact ID suffix matches, then substring
        matches. ``preferred_types`` limits the candidate node types.
        """
        if preferred_types is None or "milestone" in preferred_types:
            import re

            milestone = re.search(r"\bm(\d+\.\d+)\b", question.lower())
            if milestone:
                prefix = "m" + milestone.group(1)
                for node in self.graph.nodes.values():
                    if node.type == "milestone" and node.properties.get("tag", "").lower().startswith(prefix):
                        return node

        for term in self._extract_terms(question):
            node = self._resolve_token(term, preferred_types)
            if node is not None:
                return node
        return None

    def _resolve_token(self, token: str, preferred_types: tuple[str, ...] | None = None) -> "GraphNode | None":
        """Resolve a single raw token (identifier or label) to a graph node.

        The alias registry is consulted first (canonical domain names like
        ``Knowledge Layer`` or ``Reasoning Engine``), then exact labels, ID
        suffixes, normalized identifiers, and finally substrings. Unlike
        :meth:`_resolve_target`, the token is used verbatim, so
        underscore-prefixed names (e.g. ``_map_experiences``) resolve.
        """
        from .aliases import resolve_alias

        alias = resolve_alias(token)
        if alias is not None and alias.kind == "entity" and alias.entity_id:
            node = self.graph.nodes.get(alias.entity_id)
            if node is not None and (preferred_types is None or node.type in preferred_types):
                return node

        type_priority = {
            "domain": 0,
            "component": 1,
            "rule": 2,
            "generator": 3,
            "schema": 4,
            "adr": 5,
            "milestone": 6,
            "api_endpoint": 7,
            "cli_command": 8,
            "configuration": 9,
            "test": 10,
            "dependency": 30,
            "document": 20,
            "table_row": 21,
            "mermaid_edge": 22,
        }

        token_lower = token.lower()
        norm_lower = self._normalize_identifier(token)
        best: "GraphNode | None" = None
        best_score: int | None = None
        for node in self.graph.nodes.values():
            if preferred_types and node.type not in preferred_types:
                continue
            label_lower = node.label.lower()
            id_lower = node.id.lower()
            if token_lower == label_lower:
                score = 0
            elif id_lower == token_lower or id_lower.endswith("." + token_lower):
                score = 1
            elif id_lower == norm_lower or id_lower.endswith("." + norm_lower):
                score = 1
            elif token_lower in label_lower:
                score = 10
            elif token_lower in id_lower:
                score = 20
            else:
                continue

            type_bonus = 100 - type_priority.get(node.type, 50)
            candidate_score = score - type_bonus
            if best is None or candidate_score < best_score:
                best = node
                best_score = candidate_score

        return best

    def query(self, question: str) -> "StructuredQueryResult":
        """Execute a natural language or structured query and return structured result."""
        start_time = time.perf_counter()
        intent = classify(question)
        query_type = intent.query_type
        if query_type == "entity_lookup":
            result = self._handle_entity_lookup(question)
            if not result.get("citations") and not result.get("entities"):
                fallback = self._concept_fallback(question)
                if fallback is not None:
                    result, query_type = fallback
        elif query_type == "type_filter":
            result = self._handle_type_filter(question)
        elif query_type == "dependency_traversal":
            result = self._handle_dependency_traversal(question)
        elif query_type == "reverse_dependency":
            result = self._handle_reverse_dependency(question, intent)
        elif query_type == "data_flow_path":
            result = self._handle_data_flow_path(question, intent)
            if result["answer"].startswith("Unknown data flow"):
                fallback = self._concept_fallback(question)
                if fallback is not None:
                    result, query_type = fallback
        elif query_type == "capability_check":
            result = self._handle_capability_check(question)
            if result["answer"].startswith("Unknown capability query"):
                fallback = self._concept_fallback(question)
                if fallback is not None:
                    result, query_type = fallback
        elif query_type == "status_check":
            result = self._handle_status_check(question)
        elif query_type == "impact_analysis":
            result = self._handle_impact_analysis(question)
        elif query_type == "profile_quality_check":
            if self.profile is None:
                fallback = self._concept_fallback(question)
                if fallback is not None:
                    result, query_type = fallback
                else:
                    result = self._handle_profile_quality_check(question, intent)
            else:
                result = self._handle_profile_quality_check(question, intent)
        elif query_type == "improvement_queue":
            result = self._handle_improvement_queue()
        elif query_type == "stale_artifacts":
            result = self._handle_stale_artifacts()
        elif query_type == "search":
            result = self._handle_search(question, intent)
        else:
            fallback = self._concept_fallback(question)
            if fallback is not None:
                result, query_type = fallback
            else:
                result = self._handle_unknown(question)

        query_time_ms = int((time.perf_counter() - start_time) * 1000)

        return self._finalize(question, result, query_type, query_time_ms)

    def _finalize(self, question: str, result: dict, query_type: str, query_time_ms: int) -> "StructuredQueryResult":
        """Finish a query: optionally synthesize, otherwise format deterministically."""
        if self.synthesis_provider is not None and is_synthesis_enabled():
            pack = result.get("evidence_pack") if isinstance(result, dict) else None
            if pack is not None:
                synthesized = self._synthesize(question, pack, result, query_type, query_time_ms)
                if synthesized is not None:
                    return synthesized
        return self._format_result(result, query_type, query_time_ms)

    def _synthesize(
        self,
        question: str,
        pack: "EvidencePack",
        result: dict,
        query_type: str,
        query_time_ms: int,
    ) -> "StructuredQueryResult | None":
        """Synthesize grounded prose from a validated EvidencePack.

        Only a ``grounded`` result replaces the deterministic answer; a refusal
        or insufficient-evidence outcome falls back to the deterministic
        answer so the LLM can never degrade a grounded response.
        """
        from .synthesis import SynthesisEngine, citations_from_pack

        synthesis = SynthesisEngine(self.synthesis_provider).synthesize(question, pack)
        if synthesis.status != "grounded":
            return None
        citations = citations_from_pack(pack, synthesis.evidence_ids)
        return StructuredQueryResult(
            answer=synthesis.answer,
            citations=citations,
            matched_entities=tuple(c.entity_id for c in citations),
            traversal_path=tuple(),
            confidence=synthesis.confidence,
            entities_found=len(result.get("entities", [])),
            query_time_ms=query_time_ms,
            query_type=query_type,
        )

    def _concept_fallback(self, question: str) -> "tuple[dict, str] | None":
        """Answer via Tier 1 concept retrieval when deterministic handlers fail.

        Returns ``(result_dict, "concept_retrieval")`` when a strong,
        source-backed concept candidate exists; ``None`` otherwise so callers
        keep their original no-evidence answer.
        """
        from .concept_retrieval import ConceptRetriever
        from .rich_format import RichFormatter

        pack = ConceptRetriever(self.graph, repo_root=self.repo_root).retrieve(question)
        if pack is None:
            return None
        render = RichFormatter(self.graph, root=self.repo_root).format_evidence(pack)
        return {
            "answer": render.text,
            "citations": render.citations,
            "entities": [c["entity_id"] for c in render.citations],
            "evidence_pack": pack,
        }, "concept_retrieval"

    def _classify_query(self, question: str) -> str:
        """Classify the query type using the M1.23 deterministic grammar."""
        return classify(question).query_type

    def _has_type_keyword(self, question: str) -> bool:
        """True when the question names a CSKS entity type to list."""
        type_keywords = {
            "domain", "domains", "component", "components", "api", "endpoint",
            "endpoints", "cli", "command", "commands", "rule", "rules",
            "generator", "generators", "schema", "schemas", "test", "tests",
            "adr", "adrs", "milestone", "milestones", "config", "configuration",
            "principle", "principles",
        }
        return any(kw in question for kw in type_keywords)

    def _cluster_from_question(self, question: str) -> tuple[Any, list] | None:
        """Return (AliasEntry, [nodes]) when the question names a cluster alias."""
        from .aliases import DOMAIN_ALIASES, _fold

        folded = _fold(question)
        for entry in DOMAIN_ALIASES:
            if entry.kind != "cluster" or not entry.module_prefix:
                continue
            if _fold(entry.alias) in folded:
                nodes = [
                    n for n in self.graph.nodes.values()
                    if n.type == "component"
                    and n.properties.get("module", "").startswith(entry.module_prefix)
                ]
                return entry, nodes
        return None

    def _handle_entity_lookup(self, question: str) -> dict:
        """Handle entity lookup queries."""
        cluster = self._cluster_from_question(question)
        if cluster is not None:
            entry, nodes = cluster
            return self._format_cluster_result(entry, nodes)

        node = self._resolve_target(question)
        if node is None:
            return {"answer": f"Could not find entity matching: {question}", "citations": [], "entities": []}
        return self._format_entity_result(node, question)

    def _format_cluster_result(self, entry, nodes: list) -> dict:
        """Build a lookup result for an alias cluster (e.g. Interview Intelligence)."""
        if not nodes:
            return {
                "answer": f"{entry.canonical_name}: {entry.absent_hint or 'no matching components found.'}",
                "citations": [],
                "entities": [],
            }

        answer_lines = [f"{entry.canonical_name} ({len(nodes)} components):"]
        citations = []
        entities = []
        for node in sorted(nodes, key=lambda n: n.label)[:50]:
            answer_lines.append(f"  - {node.label} ({node.id})")
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{node.label} - {node.type}",
                "entity_id": node.id,
            })
        answer_lines.append("")
        answer_lines.append(entry.absent_hint)
        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _format_entity_result(self, node: "GraphNode", question: str = "") -> dict:
        """Build a lookup result describing a single entity."""
        from .rich_format import RichFormatter

        if node.type == "document":
            pack = self._retrieve_document_evidence(node, question)
            render = RichFormatter(self.graph, root=self.repo_root).format_evidence(pack)
            return {
                "answer": render.text,
                "citations": render.citations,
                "entities": [node.id],
                "evidence_pack": pack,
            }

        if node.type in RichFormatter._SPECIALISED:
            render = RichFormatter(self.graph, root=self.repo_root).format(node)
            return {
                "answer": render.text,
                "citations": render.citations,
                "entities": [node.id],
            }

        props = node.properties
        detail_lines = [
            f"{node.type.title()}: {node.label} ({node.id})",
            "",
            "Properties:",
        ]
        for key in sorted(props):
            if key in ("source_path", "line_start", "line_end", "confidence"):
                continue
            value = props[key]
            if isinstance(value, (list, dict)):
                value = json.dumps(value) if len(json.dumps(value)) < 300 else str(value)[:300]
            detail_lines.append(f"  {key}: {value}")

        citation = {
            "file": props.get("source_path", ""),
            "line_start": props.get("line_start", 0),
            "line_end": props.get("line_end", 0),
            "text": f"{node.label} - {node.type}",
            "entity_id": node.id,
        }
        return {
            "answer": "\n".join(detail_lines),
            "citations": [citation],
            "entities": [node.id],
        }

    def _retrieve_document_evidence(self, node: "GraphNode", question: str) -> "EvidencePack":
        """Assemble a bounded EvidencePack for a resolved document node.

        The primary evidence is the node's own source-backed section text.
        Related evidence is selected from other indexed document nodes (Markdown
        sources only) whose section text opens with the primary label followed
        by a definitional clause ("<label> is a/an/the ...") or a goal clause
        ("<label> addresses/provides/supports/aims ..."). Selection is
        deterministic: definitional statements rank above goal statements, then
        by source path, then by line; duplicates share the same text; at most
        two related pieces of evidence are kept.
        """
        from .rich_format import RichFormatter

        formatter = RichFormatter(self.graph, root=self.repo_root)
        primary = CSKSEvidence(
            entity_id=node.id,
            label=node.label,
            source_path=node.properties.get("source_path", ""),
            line_start=node.properties.get("line_start", 0),
            line_end=node.properties.get("line_end", 0),
            text=formatter.document_text(node) or "",
            role="primary",
        )

        label = node.label.lower()
        definitions = tuple(label + suffix for suffix in self._DEFINITION_PREFIXES)
        goals = tuple(label + suffix for suffix in self._GOAL_PREFIXES)

        candidates: list[tuple[int, str, int, "CSKSEvidence"]] = []
        for other in self.graph.nodes.values():
            if other.id == node.id or other.type != "document":
                continue
            path = other.properties.get("source_path", "")
            if not path.endswith(".md"):
                continue
            text = formatter.document_text(other)
            if not text:
                continue
            lowered = text.lower()
            if lowered.startswith(definitions):
                rank = 0
            elif lowered.startswith(goals):
                rank = 1
            else:
                continue
            candidates.append((
                rank,
                path,
                other.properties.get("line_start", 0),
                CSKSEvidence(
                    entity_id=other.id,
                    label=other.label,
                    source_path=path,
                    line_start=other.properties.get("line_start", 0),
                    line_end=other.properties.get("line_end", 0),
                    text=text,
                    role="related",
                ),
            ))

        seen: set[tuple[str, str]] = set()
        related: list["CSKSEvidence"] = []
        for _rank, _path, _line, evidence in sorted(candidates, key=lambda item: (item[0], item[1], item[2])):
            key = (evidence.source_path, evidence.text)
            if key in seen:
                continue
            seen.add(key)
            related.append(evidence)
            if len(related) == 2:
                break

        return EvidencePack(query=question, primary=primary, related=tuple(related))

    def _handle_type_filter(self, question: str) -> dict:
        """Handle type filter queries (e.g., 'list all domains')."""
        type_keywords = {
            "domain": "domain",
            "domains": "domain",
            "component": "component",
            "components": "component",
            "api": "api_endpoint",
            "endpoint": "api_endpoint",
            "cli": "cli_command",
            "command": "cli_command",
            "rule": "rule",
            "rules": "rule",
            "generator": "generator",
            "generators": "generator",
            "schema": "schema",
            "schemas": "schema",
            "test": "test",
            "tests": "test",
            "adr": "adr",
            "adrs": "adr",
            "milestone": "milestone",
            "milestones": "milestone",
            "config": "configuration",
            "configuration": "configuration",
            "principle": "principle",
            "principles": "principle",
        }

        q = question.lower()
        target_type = None
        for keyword, etype in type_keywords.items():
            if keyword in question.lower():
                target_type = etype
                break

        if not target_type:
            # Try to infer from "list all X"
            import re
            match = re.search(r"list all (\w+)", question.lower())
            if match:
                target_type = match.group(1)

        if not target_type:
            return {"answer": "Could not determine what type to list. Try 'list domains', 'list rules', etc.", "citations": [], "entities": []}

        matches = [n for n in self.graph.nodes.values() if n.type == target_type]
        if not matches:
            return {"answer": f"No entities of type '{target_type}' found.", "citations": [], "entities": []}

        import re

        filter_terms = self._extract_terms(question)
        extra_tokens = [
            t for t in re.findall(r"[A-Za-z][A-Za-z0-9_.-]*", question)
            if t.lower() not in type_keywords
            and t.lower() not in self._STOPWORDS
            and t.lower() not in ("all", "list", "show", "enumerate")
            and len(t) >= 3
        ]
        filter_terms += [t for t in extra_tokens if t.lower() not in {f.lower() for f in filter_terms}]
        if filter_terms:
            filtered = []
            for node in matches:
                haystack = f"{node.id} {node.label}".lower()
                if all(term.lower() in haystack for term in filter_terms):
                    filtered.append(node)
            if filtered:
                matches = filtered

        answer_lines = [f"Found {len(matches)} {target_type}(s):"]
        citations = []
        entities = []

        for node in sorted(matches, key=lambda n: n.label):
            answer_lines.append(f"  - {node.label} ({node.id})")
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{node.label} - {node.type}",
                "entity_id": node.id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": [n.id for n in matches],
        }

    @staticmethod
    def _describe_node(node: "GraphNode") -> str:
        """Human-readable description of a dependent node."""
        if node.type == "dependency":
            source = node.properties.get("source_module", "")
            imported = node.properties.get("imported_name", node.label)
            return f"{imported} (imported by {source}.py)"
        return f"{node.label} ({node.id})"

    def _handle_dependency_traversal(self, question: str) -> dict:
        """Handle dependency traversal queries."""
        target = self._resolve_target(question, preferred_types=("domain", "component", "rule", "generator"))

        if not target:
            return {"answer": "Could not identify target entity for dependency traversal.", "citations": [], "entities": []}

        # Find reverse dependencies (what depends on target)
        dependents = self._find_dependents(target.id)

        if not dependents:
            return {"answer": f"Nothing depends on {target.label} ({target.id}).", "citations": [], "entities": []}

        answer_lines = [f"{len(dependents)} entit(y/ies) depend on {target.label} ({target.id}):"]
        citations = []
        entities = []

        for node in sorted(dependents, key=lambda n: n.label):
            answer_lines.append(f"  - {self._describe_node(node)}")
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{node.label} depends on {target.label}",
                "entity_id": node.id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": [n.id for n in dependents],
        }

    def _find_dependents(self, target_id: str, visited: set | None = None) -> list:
        """Find all entities that transitively depend on the target."""
        if visited is None:
            visited = set()

        dependents = []
        # Look for edges where target_id is the target (reverse dependency)
        for edge in self.graph._incoming.get(target_id, []):
            if edge.source_id not in visited:
                source_node = self.graph.nodes.get(edge.source_id)
                if source_node:
                    dependents.append(source_node)
                    visited.add(edge.source_id)
                    # Recursively find dependents of the dependent
                    dependents.extend(self._find_dependents(edge.source_id, visited))

        return dependents

    def _handle_data_flow_path(self, question: str, intent: "ClassifiedIntent | None" = None) -> dict:
        """Handle data flow path queries."""
        # Look for known data flow patterns
        flow_patterns = {
            "artifact generation": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate"],
            "artifact": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate"],
            "cv": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate", "Render CV"],
            "cv generation": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate", "Render CV"],
            "acquisition": ["Source DOCX", "Reader", "Text Extractor", "LLM Extractor", "Canonical Profile Builder", "Validator", "YAML Writer"],
            "reasoning": ["Profile", "Graph Build", "Rule Execution", "Result Assembly"],
            "ai": ["Profile", "Graph Build", "Rule Execution", "Result Assembly"],
            "recommendations": ["Profile", "Quality", "Findings", "Unified Recommendations", "Improvement Queue"],
            "recommendation": ["Profile", "Quality", "Findings", "Unified Recommendations", "Improvement Queue"],
            "interview preparation": ["Profile", "Load", "Knowledge Graph", "Reasoning", "Interview Simulation", "Preparation Guide Generator"],
        }

        q = question.lower()
        topic = (intent.target or "").lower() if intent else ""
        haystack = f"{topic} {q}"
        matched_flow = None
        for pattern, steps in flow_patterns.items():
            if pattern in haystack:
                matched_flow = steps
                flow_label = pattern
                break

        if not matched_flow:
            return {"answer": "Unknown data flow. Known flows: 'artifact generation', 'cv', 'interview preparation', 'acquisition', 'reasoning', 'ai', 'recommendations'.", "citations": [], "entities": []}

        answer_lines = [f"Data flow for {flow_label}:"]
        for i, step in enumerate(matched_flow, 1):
            answer_lines.append(f"  {i}. {step}")

        # Find related entities in the graph
        related_entities = []
        for node in self.graph.nodes.values():
            if node.type in ("dataflow", "component", "domain") and any(step.lower() in node.label.lower() for step in matched_flow):
                related_entities.append(node)

        citations = []
        entities = []
        for node in related_entities[:10]:
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{node.label} - {node.type}",
                "entity_id": node.id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _handle_reverse_dependency(self, question: str, intent: "ClassifiedIntent | None" = None) -> dict:
        """Handle reverse dependency queries (what does X depend on)."""
        target = None
        preferred = ("component", "rule", "generator", "domain", "schema", "api_endpoint")
        if intent is not None and intent.target:
            target = self._resolve_token(intent.target, preferred)
        if target is None:
            target = self._resolve_target(question, preferred_types=preferred)

        if not target:
            return {"answer": "Could not identify target entity for dependency analysis.", "citations": [], "entities": []}

        # What the target consumes: explicit outgoing edges plus import edges
        # captured by dependency nodes whose source module matches the target.
        dependencies = self._dependencies_of(target)

        if not dependencies:
            return {"answer": f"{target.label} ({target.id}) has no known dependencies.", "citations": [], "entities": []}

        answer_lines = [f"{target.label} ({target.id}) depends on {len(dependencies)} entit(y/ies):"]
        citations = []
        entities = []
        for node in sorted(dependencies, key=lambda n: n.label):
            answer_lines.append(f"  - {self._describe_node(node)}")
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{target.label} depends on {node.label}",
                "entity_id": node.id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": [n.id for n in dependencies],
        }

    def _dependencies_of(self, node: "GraphNode") -> list["GraphNode"]:
        """Return what a node depends on, deterministically.

        Combines explicit outgoing ``depends_on`` edges with the import
        relationships captured by ``dependency`` nodes whose ``source_module``
        matches the node's module. When the builder could not link an import
        to a node (e.g. generator entities with type-prefixed ids), the
        imported name is resolved by exact label.
        """
        results: dict[str, "GraphNode"] = {}
        for edge in self.graph._outgoing.get(node.id, []):
            target = self.graph.nodes.get(edge.target_id)
            if target:
                results[target.id] = target

        module = node.properties.get("module", "")
        if module:
            for dep in self.graph.nodes.values():
                if dep.type != "dependency":
                    continue
                if dep.properties.get("source_module") != module:
                    continue
                edge_targets = [
                    t for t in (self.graph.nodes.get(e.target_id) for e in self.graph._outgoing.get(dep.id, []))
                    if t is not None
                ]
                if edge_targets:
                    for target in edge_targets:
                        results[target.id] = target
                    continue
                resolved = self._resolve_imported(dep)
                if resolved is not None:
                    results[resolved.id] = resolved
        return list(results.values())

    def _resolve_imported(self, dep: "GraphNode") -> "GraphNode | None":
        """Resolve a dependency node's imported name to a graph entity by label."""
        imported_name = dep.properties.get("imported_name", "")
        if not imported_name or not re.match(r"[A-Za-z_]\w*$", imported_name):
            return None

        priority = {
            "domain": 0, "component": 1, "rule": 2, "generator": 3,
            "schema": 4, "adr": 5, "milestone": 6, "api_endpoint": 7,
            "cli_command": 8, "configuration": 9, "test": 10,
        }
        best: "GraphNode | None" = None
        best_rank = -1
        for candidate in self.graph.nodes.values():
            if candidate.type not in priority:
                continue
            if candidate.label != imported_name:
                continue
            rank = priority[candidate.type]
            if best is None or rank < best_rank:
                best = candidate
                best_rank = rank
        return best

    def _handle_search(self, question: str, intent: "ClassifiedIntent | None" = None) -> dict:
        """Handle search queries by delegating to the grouped term search."""
        from .search import grouped_search

        term = (intent.target if intent else None) or question.strip()
        term = term.strip(" .?!")

        groups = grouped_search(self.graph, term)
        total = groups["total"]
        if total == 0:
            return {
                "answer": f"No entities found matching '{term}'.",
                "citations": [],
                "entities": [],
            }

        answer_lines = [f'Search results for "{term}":']
        citations = []
        entities = []
        for group_name in ("Domains", "Components", "APIs", "Schemas", "Rules",
                           "Generators", "Tests", "Milestones", "ADRs",
                           "CLI commands", "Configurations", "Documents"):
            items = groups["groups"].get(group_name, [])
            if not items:
                continue
            answer_lines.append(f"{group_name}:")
            for item in items:
                answer_lines.append(f"  - {item['label']} ({item['id']}) — {item['location']}")
                entities.append(item["id"])
                citations.append({
                    "file": item["file"],
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                    "text": f"{item['label']} - {item['type']}",
                    "entity_id": item["id"],
                })

        answer_lines.append(f"Total matches: {total}")
        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _handle_capability_check(self, question: str) -> dict:
        """Handle capability check queries."""
        capabilities = {
            "pdf": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "pdf generation": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "pdf export": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "llm": "No LLM in M1.22 - CSKS is purely deterministic. LLM formatting layer planned for M1.25.",
            "llm integration": "No LLM in M1.22 - CSKS is purely deterministic. LLM formatting layer planned for M1.25.",
            "ai": "No LLM in M1.22 - CSKS is purely deterministic.",
            "incremental": "Yes - incremental indexing re-indexes only changed files via 'careeros csks index --incremental'.",
            "incremental indexing": "Yes - incremental indexing re-indexes only changed files via 'careeros csks index --incremental'.",
        }

        q = question.lower()
        for keyword, answer in capabilities.items():
            if keyword in q:
                return {"answer": answer, "citations": [], "entities": []}

        return {"answer": "Unknown capability query. Known capabilities: PDF generation, LLM integration, incremental indexing.", "citations": [], "entities": []}

    def _handle_status_check(self, question: str) -> dict:
        """Handle status check queries."""
        milestones = {
            "m1.19": {"status": "completed", "tag": "m1.19-interview-api", "title": "Interview Simulation API"},
            "m1.20": {"status": "completed", "tag": "m1.20-interview-preparation", "title": "Interview Preparation Frontend"},
            "m1.21": {"status": "completed", "tag": "m1.21-artifact-workspace", "title": "Artifact Workspace"},
            "m1.22": {"status": "in_progress", "tag": "m1.22-csks-foundation", "title": "CSKS Foundation"},
        }

        q = question.lower()
        for key, info in milestones.items():
            if key in q:
                return {
                    "answer": f"M1.{key.split('.')[-1]} ({info['title']}): {info['status'].title()} (tag: {info['tag']})",
                    "citations": [],
                    "entities": [f"milestone.{key}"],
                }

        if "m1" in q:
            return {
                "answer": "Available milestones: " + ", ".join(f"M1.{k.split('.')[-1]} ({v['title']}) - {v['status']}" for k, v in milestones.items()),
                "citations": [],
                "entities": [f"milestone.{k}" for k in milestones],
            }

        return {"answer": "Unknown status query. Try 'M1.21 status' or 'M1.22 status'.", "citations": [], "entities": []}

    def _handle_impact_analysis(self, question: str) -> dict:
        """Handle impact analysis queries."""
        target = self._resolve_target(question, preferred_types=("component", "rule", "generator", "domain"))

        if not target:
            return {"answer": "Could not identify target for impact analysis.", "citations": [], "entities": []}

        # Find all dependents (what breaks if this changes)
        dependents = self._find_dependents(target.id)

        if not dependents:
            return {"answer": f"Changing {target.label} ({target.id}) has no known dependents.", "citations": [], "entities": []}

        answer_lines = [f"Changing {target.label} ({target.id}) would affect {len(dependents)} entit(y/ies):"]
        citations = []
        entities = []

        for node in sorted(dependents, key=lambda n: n.label):
            answer_lines.append(f"  - {self._describe_node(node)}")
            entities.append(node.id)
            citations.append({
                "file": node.properties.get("source_path", ""),
                "line_start": node.properties.get("line_start", 0),
                "line_end": node.properties.get("line_end", 0),
                "text": f"{node.label} depends on {target.label}",
                "entity_id": node.id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": [n.id for n in dependents],
        }

    def _handle_profile_quality_check(
        self, question: str, intent: "ClassifiedIntent | None" = None
    ) -> dict:
        """Answer profile health / narrative-quality questions deterministically.

        Runs the Profile Quality Engine over the profile attached to the query
        engine (``profile`` constructor argument). Narrative questions report
        the duplicated narrative, every entity carrying it, and the occurrence
        count; generic health questions report the health score, the dimensions
        below full health, and the findings with citations.
        """
        if self.profile is None:
            return {
                "answer": (
                    "No profile is attached to the query engine. Provide a "
                    "canonical profile (CSKSQueryEngine(graph, profile=...)) to "
                    "answer profile-quality questions."
                ),
                "citations": [],
                "entities": [],
            }

        from careeros.profile_quality import run_profile_quality

        report = run_profile_quality(self.profile)
        q = question.lower()

        if "narrative" in q or "duplicate" in q:
            findings = [
                f for f in report.findings
                if f.rule_id == "recommendation_remove_duplicate_narrative"
            ]
            if not findings:
                return {
                    "answer": (
                        f"No duplicate narrative found. Profile "
                        f"'{report.profile_id}' health score is "
                        f"{report.health_score}/100."
                    ),
                    "citations": [],
                    "entities": [],
                }

            answer_lines = [
                f"Profile '{report.profile_id}' contains {len(findings)} duplicate "
                "narrative group(s):"
            ]
            citations: list[dict] = []
            entities: list[str] = []
            for finding in findings:
                occurrences = finding.citations
                snippet = occurrences[0].snippet if occurrences else ""
                locations = ", ".join(
                    f"{citation.entity_id} ({citation.entity_type})"
                    for citation in occurrences
                )
                answer_lines.append(
                    f"  - '{snippet}' appears {len(occurrences)} times"
                )
                answer_lines.append(f"    Locations: {locations}")
                answer_lines.append(f"    Action: {finding.suggested_action}")
                for citation in occurrences:
                    entities.append(citation.entity_id)
                    citations.append({
                        "file": report.profile_id,
                        "line_start": 0,
                        "line_end": 0,
                        "text": citation.snippet,
                        "entity_id": citation.entity_id,
                    })
            return {
                "answer": "\n".join(answer_lines),
                "citations": citations,
                "entities": entities,
            }

        answer_lines = [
            f"Profile '{report.profile_id}' health score: {report.health_score}/100."
        ]
        below = [d for d in report.dimension_scores if d.score < 1.0]
        if not below:
            answer_lines.append(
                "All dimensions are healthy — the profile is fully optimized."
            )
            return {"answer": "\n".join(answer_lines), "citations": [], "entities": []}

        answer_lines.append(f"{len(below)} dimension(s) below full health:")
        for dimension in below:
            answer_lines.append(f"  - {dimension.name} ({dimension.score:.0%})")
        answer_lines.append("Findings:")
        citations: list[dict] = []
        entities: list[str] = []
        for finding in report.findings:
            answer_lines.append(f"  - [{finding.rule_id}] {finding.title}")
            entities.append(finding.element_id)
            citations.append({
                "file": report.profile_id,
                "line_start": 0,
                "line_end": 0,
                "text": finding.title,
                "entity_id": finding.element_id,
            })
        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _handle_improvement_queue(self) -> dict:
        """Answer 'list improvements' deterministically.

        Runs the Profile Quality Engine over the attached profile and renders
        the prioritized improvement queue from the unified recommendation
        model (ADR-009), matching ``careeros improvement-queue`` ordering.
        """
        if self.profile is None:
            return {
                "answer": (
                    "No profile is attached to the query engine. Provide a "
                    "canonical profile (CSKSQueryEngine(graph, profile=...)) to "
                    "answer improvement questions."
                ),
                "citations": [],
                "entities": [],
            }

        from careeros.profile_quality import (
            filter_and_sort_recommendations,
            run_profile_quality,
            to_unified_recommendations,
        )

        report = run_profile_quality(self.profile)
        recommendations = filter_and_sort_recommendations(
            to_unified_recommendations(report)
        )

        if not recommendations:
            return {
                "answer": (
                    f"Profile '{report.profile_id}' has no pending "
                    "improvements - the profile is fully optimized."
                ),
                "citations": [],
                "entities": [],
            }

        answer_lines = [
            f"Profile '{report.profile_id}' improvement queue "
            f"({len(recommendations)} item(s)):"
        ]
        citations: list[dict] = []
        entities: list[str] = []
        for recommendation in recommendations:
            answer_lines.append(
                f"  - [{recommendation.priority}] {recommendation.title} "
                f"({recommendation.rule_id})"
            )
            answer_lines.append(f"    Action: {recommendation.suggested_action}")
            answer_lines.append(
                f"    Resolution: {recommendation.resolution_type} on "
                f"{recommendation.element_id}"
            )
            entities.append(recommendation.element_id)
            citations.append({
                "file": report.profile_id,
                "line_start": 0,
                "line_end": 0,
                "text": recommendation.title,
                "entity_id": recommendation.element_id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _handle_stale_artifacts(self) -> dict:
        """Answer 'show stale artifacts' deterministically.

        Reuses the canonical artifact lifecycle state written by the
        Resolution Engine (``careeros.resolution``: an artifact's ``status``
        is set to ``stale`` when a resolution mutates an element it exports).
        Nothing is regenerated here - regeneration is an explicit user action.
        """
        if self.profile is None:
            return {
                "answer": (
                    "No profile is attached to the query engine. Provide a "
                    "canonical profile (CSKSQueryEngine(graph, profile=...)) to "
                    "answer stale-artifact questions."
                ),
                "citations": [],
                "entities": [],
            }

        profile_id = str(self.profile.get("person", {}).get("id", "unknown"))
        stale = [
            artifact
            for artifact in self.profile.get("artifacts", [])
            if isinstance(artifact, dict) and artifact.get("status") == "stale"
        ]

        if not stale:
            return {
                "answer": (
                    f"Profile '{profile_id}' has no stale artifacts - all "
                    "generated artifacts are current."
                ),
                "citations": [],
                "entities": [],
            }

        answer_lines = [
            f"Profile '{profile_id}' has {len(stale)} stale artifact(s) - "
            "regenerate them to reflect the updated canonical profile:"
        ]
        citations: list[dict] = []
        entities: list[str] = []
        for artifact in stale:
            artifact_id = str(artifact.get("id", "") or "?")
            title = str(artifact.get("title", "") or artifact_id)
            artifact_type = str(artifact.get("artifactType", "") or "")
            answer_lines.append(f"  - {title} ({artifact_id}) [{artifact_type}]")
            entities.append(artifact_id)
            citations.append({
                "file": profile_id,
                "line_start": 0,
                "line_end": 0,
                "text": f"{title} is stale",
                "entity_id": artifact_id,
            })

        return {
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "entities": entities,
        }

    def _handle_unknown(self, question: str) -> dict:
        from .grammar import suggest

        suggestions = suggest(question)
        answer_lines = ["I could not classify your query.", "Did you mean:"]
        for suggestion in suggestions:
            answer_lines.append(f"  - {suggestion}")
        return {
            "answer": "\n".join(answer_lines),
            "citations": [],
            "entities": [],
        }

    def _format_result(self, result: dict, query_type: str, query_time_ms: int) -> "StructuredQueryResult":
        citations = tuple(
            Citation(
                file=c["file"],
                line_start=c["line_start"],
                line_end=c["line_end"],
                text=c["text"],
                entity_id=c["entity_id"],
            )
            for c in result.get("citations", [])
        )

        confidence = 1.0 if result.get("entities") and result.get("citations") else 0.0
        return StructuredQueryResult(
            answer=result["answer"],
            citations=citations,
            matched_entities=tuple(result.get("entities", [])),
            traversal_path=tuple(),
            confidence=confidence,
            entities_found=len(result.get("entities", [])),
            query_time_ms=query_time_ms,
            query_type=query_type,
        )


class AnswerFormatter:
    """Formats structured query results for CLI or API output."""

    @staticmethod
    def format_cli(result: StructuredQueryResult) -> str:
        """Format result for CLI output."""
        lines = [result.answer]
        if result.citations:
            lines.append("")
            lines.append("Sources:")
            for i, citation in enumerate(result.citations, 1):
                lines.append(f"  [{i}] {citation.file}:{citation.line_start}-{citation.line_end}")
                lines.append(f"      {citation.text[:100]}")
        lines.append("")
        lines.append(f"Entities found: {result.entities_found}")
        lines.append(f"Query time: {result.query_time_ms}ms")
        lines.append(f"Confidence: {result.confidence:.0%}")
        return "\n".join(lines)

    @staticmethod
    def format_json(result: StructuredQueryResult) -> dict:
        """Format result for JSON API response."""
        return {
            "answer": result.answer,
            "citations": [
                {
                    "file": c.file,
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                    "text": c.text,
                    "entity_id": c.entity_id,
                }
                for c in result.citations
            ],
            "confidence": result.confidence,
            "entities_found": result.entities_found,
            "query_time_ms": result.query_time_ms,
            "query_type": result.query_type,
        }