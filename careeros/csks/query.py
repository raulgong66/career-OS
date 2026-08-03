from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Literal

from careeros.knowledge import GraphEdge, GraphNode, KnowledgeGraph

from .models import (
    Citation,
    StructuredQueryResult,
    CSKSAnswer,
    QueryType,
    make_entity_id,
)


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

    def __init__(self, graph: "KnowledgeGraph") -> None:
        self.graph = graph
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

        # CamelCase identifiers (e.g. InterviewEngine, ProfileLoader)
        candidates += re.findall(r'\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)*\b', question)

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

    def _resolve_target(self, question: str, preferred_types: tuple[str, ...] | None = None) -> "GraphNode | None":
        """Find the best-matching entity node for a question.

        Exact label matches win, then exact ID suffix matches, then substring
        matches. ``preferred_types`` limits the candidate node types; otherwise
        all types compete and a type-priority ranking breaks ties.
        """
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

        terms = self._extract_terms(question)
        for term in terms:
            term_lower = term.lower()
            best: "GraphNode | None" = None
            best_score: int | None = None
            for node in self.graph.nodes.values():
                if preferred_types and node.type not in preferred_types:
                    continue
                label_lower = node.label.lower()
                id_lower = node.id.lower()
                if term_lower == label_lower:
                    score = 0
                elif id_lower == term_lower or id_lower.endswith("." + term_lower):
                    score = 1
                elif term_lower in label_lower:
                    score = 10
                elif term_lower in id_lower:
                    score = 20
                else:
                    continue

                type_bonus = 100 - type_priority.get(node.type, 50)
                candidate_score = score - type_bonus
                if best is None or candidate_score < best_score:
                    best = node
                    best_score = candidate_score

            if best is not None:
                return best
        return None

    def query(self, question: str) -> "StructuredQueryResult":
        """Execute a natural language or structured query and return structured result."""
        start_time = time.perf_counter()
        query_type = self._classify_query(question)
        if query_type == "entity_lookup":
            result = self._handle_entity_lookup(question)
        elif query_type == "type_filter":
            result = self._handle_type_filter(question)
        elif query_type == "dependency_traversal":
            result = self._handle_dependency_traversal(question)
        elif query_type == "data_flow_path":
            result = self._handle_data_flow_path(question)
        elif query_type == "capability_check":
            result = self._handle_capability_check(question)
        elif query_type == "status_check":
            result = self._handle_status_check(question)
        elif query_type == "impact_analysis":
            result = self._handle_impact_analysis(question)
        else:
            result = self._handle_unknown(question)

        query_time_ms = int((time.perf_counter() - start_time) * 1000)

        return self._format_result(result, query_type, query_time_ms)

    def _classify_query(self, question: str) -> str:
        """Classify the query type based on keywords."""
        q = question.lower()

        if any(kw in q for kw in ["what is", "what are", "define", "describe", "tell me about"]):
            return "entity_lookup"
        elif any(kw in q for kw in ["list", "show all", "enumerate"]):
            return "type_filter"
        elif any(kw in q for kw in ["depends on", "depends upon", "dependencies of", "what depends on", "who uses"]):
            return "dependency_traversal"
        elif any(kw in q for kw in ["data flow", "flow", "pipeline", "steps", "sequence"]):
            return "data_flow_path"
        elif any(kw in q for kw in ["support", "capability", "does careeros", "is there", "can careeros"]):
            return "capability_check"
        elif any(kw in q for kw in ["status", "version", "tag", "milestone"]):
            return "status_check"
        elif any(kw in q for kw in ["breaks", "impact", "affect", "what breaks", "impact of"]):
            return "impact_analysis"
        elif self._has_type_keyword(q):
            return "type_filter"
        return "unknown"

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

    def _handle_entity_lookup(self, question: str) -> dict:
        """Handle entity lookup queries."""
        node = self._resolve_target(question)
        if node is None:
            return {"answer": f"Could not find entity matching: {question}", "citations": [], "entities": []}
        return self._format_entity_result(node)

    def _format_entity_result(self, node: "GraphNode") -> dict:
        """Build a lookup result describing a single entity."""
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

    def _handle_data_flow_path(self, question: str) -> dict:
        """Handle data flow path queries."""
        # Look for known data flow patterns
        flow_patterns = {
            "artifact generation": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate"],
            "artifact": ["Profile", "Load", "Validate", "Knowledge Graph", "Reasoning", "Contract", "Generate"],
            "acquisition": ["Source DOCX", "Reader", "Text Extractor", "LLM Extractor", "Canonical Profile Builder", "Validator", "YAML Writer"],
            "reasoning": ["Profile", "Graph Build", "Rule Execution", "Result Assembly"],
        }

        q = question.lower()
        matched_flow = None
        for pattern, steps in flow_patterns.items():
            if pattern in q:
                matched_flow = steps
                break

        if not matched_flow:
            return {"answer": "Unknown data flow. Known flows: 'artifact generation', 'acquisition', 'reasoning'.", "citations": [], "entities": []}

        answer_lines = [f"Data flow for artifact generation:"]
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

    def _handle_capability_check(self, question: str) -> dict:
        """Handle capability check queries."""
        capabilities = {
            "pdf": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "pdf generation": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "pdf export": "No - only Markdown and DOCX formats are supported for artifact generation.",
            "llm": "No LLM in M1.22 - CSKS is purely deterministic. LLM formatting layer planned for M1.25.",
            "llm integration": "No LLM in M1.22 - CSKS is purely deterministic. LLM formatting layer planned for M1.25.",
            "ai": "No LLM in M1.22 - CSKS is purely deterministic.",
            "incremental": "Incremental indexing is deferred to M1.23.",
            "incremental indexing": "Incremental indexing is deferred to M1.23.",
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

    def _handle_unknown(self, question: str) -> dict:
        return {
            "answer": f"Unknown query type. Try: 'What is X?', 'List all domains', 'What depends on X?', 'Data flow for artifact generation', 'M1.21 status', 'What breaks if I change ProfileLoader?'",
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

        return StructuredQueryResult(
            answer=result["answer"],
            citations=citations,
            matched_entities=tuple(result.get("entities", [])),
            traversal_path=tuple(),
            confidence=1.0,
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