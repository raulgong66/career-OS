"""Rich, deterministic answer formatting for CSKS entities (M1.23).

Renders Components, Domains, ADRs, Milestones, Rules, and Generators as
sectioned, human-readable text derived entirely from the knowledge graph.
"Purpose" text is enriched deterministically from the node's own source file
(docstring for Python, table row for the domain map, description for
schemas); when enrichment is unavailable the formatter falls back to
structured facts and never fabricates prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RichRender:
    """Text plus the citations backing that text."""

    text: str
    citations: list[dict]


class RichFormatter:
    """Formats a single graph node into a rich, cited answer."""

    _SPECIALISED = frozenset({"component", "rule", "generator", "domain", "adr", "milestone", "schema"})

    def __init__(self, graph, root: "Path | None" = None) -> None:
        self.graph = graph
        self.root = root
        self._purpose_cache: dict[tuple[str, int], str | None] = {}

    def _resolve(self, path: str) -> "Path":
        """Resolve a repo-relative source path against the configured root."""
        if self.root is not None:
            return self.root / path
        return Path(path)

    # --- public entry point -------------------------------------------------

    def format(self, node) -> "RichRender":
        """Render a node; returns text plus citation dicts."""
        if node.type == "component":
            return self._component(node)
        if node.type == "rule":
            return self._component(node, header="Rule")
        if node.type == "generator":
            return self._component(node, header="Generator")
        if node.type == "domain":
            return self._domain(node)
        if node.type == "adr":
            return self._adr(node)
        if node.type == "milestone":
            return self._milestone(node)
        if node.type == "schema":
            return self._schema(node)
        return self._generic(node)

    # --- component/rule/generator ------------------------------------------

    def _component(self, node, header: str = "Component") -> "RichRender":
        props = node.properties
        lines: list[str] = [f"{header}: {node.label} ({node.id})"]

        type_ = props.get("type", node.type)
        module = props.get("module", "")
        lines.append(f"  Type: {type_}")
        if module:
            lines.append(f"  Module: {module}")

        purpose = self._purpose(node)
        if purpose:
            lines.append(f"  Purpose: {purpose}")
        elif module:
            lines.append(f"  Purpose: A {type_} in module {module}.")

        methods = props.get("methods") or []
        if methods:
            lines.append("  Responsibilities:")
            lines.extend(f"    - {m}" for m in methods)
        public = [m for m in methods if not m.startswith("_")]
        if public:
            lines.append("  Public API:")
            lines.extend(f"    - {m}" for m in public)

        lines.extend(self._section("Depends on", self._describe_outgoing(node)))
        lines.extend(self._section("Used by", self._describe_incoming(node, exclude_tests=True)))
        lines.extend(self._section("Tests", self._describe_tests(node)))
        lines.extend(self._section("Related ADRs", self._describe_adrs(node)))
        lines.extend(self._section("Related milestones", self._describe_milestones(node)))

        source = self._source(node)
        if source:
            lines.append(f"  Source: {source}")

        return RichRender("\n".join(lines), self._citations(node))

    # --- domain -------------------------------------------------------------

    def _domain(self, node) -> "RichRender":
        props = node.properties
        lines: list[str] = [f"Domain: {node.label} ({node.id})"]

        purpose = self._domain_purpose(node)
        if purpose:
            lines.append(f"  Purpose: {purpose}")
        else:
            lines.append(f"  Purpose: {props.get('name', node.label)} domain.")

        lines.extend(self._section("Dependencies", self._describe_outgoing(node)))
        lines.extend(self._section("Used by", self._describe_incoming(node, exclude_tests=True)))

        source = self._source(node)
        if source:
            lines.append(f"  Source: {source}")

        return RichRender("\n".join(lines), self._citations(node))

    # --- ADR ----------------------------------------------------------------

    def _adr(self, node) -> "RichRender":
        props = node.properties
        number = props.get("number", "?")
        if isinstance(number, int):
            number = f"{number:03d}"
        lines: list[str] = [f"ADR-{number} ({node.id})"]
        lines.append(f"  Title: {props.get('title', node.label)}")
        lines.append(f"  Status: {props.get('status', 'unknown')}")

        purpose = self._adr_summary(props.get("source_path", ""))
        if purpose:
            lines.append(f"  Summary: {purpose}")

        source = self._source(node)
        if source:
            lines.append(f"  Source: {source}")

        return RichRender("\n".join(lines), self._citations(node))

    # --- milestone ----------------------------------------------------------

    def _milestone(self, node) -> "RichRender":
        props = node.properties
        tag = props.get("tag", "")
        summary = self._milestone_summary(props.get("title", node.label))
        lines: list[str] = [f"Milestone: {tag} ({node.id})"]
        lines.append(f"  Status: {props.get('status', 'unknown')}")
        lines.append(f"  Tag: {tag}")
        if summary:
            lines.append(f"  Summary: {summary}")
        lines.append("  Source: git tag")

        return RichRender("\n".join(lines), self._citations(node))

    # --- schema -------------------------------------------------------------

    def _schema(self, node) -> "RichRender":
        props = node.properties
        lines: list[str] = [f"Schema: {node.label} ({node.id})"]
        if props.get("title"):
            lines.append(f"  Title: {props['title']}")
        if props.get("description"):
            lines.append(f"  Description: {props['description']}")
        if props.get("type"):
            lines.append(f"  Type: {props['type']}")
        if props.get("properties"):
            lines.append("  Properties:")
            lines.extend(f"    - {p}" for p in props["properties"])
        if props.get("required"):
            lines.append(f"  Required: {', '.join(props['required'])}")

        source = self._source(node)
        if source:
            lines.append(f"  Source: {source}")

        return RichRender("\n".join(lines), self._citations(node))

    # --- generic fallback ---------------------------------------------------

    def _generic(self, node) -> "RichRender":
        lines = [f"{node.type.title()}: {node.label} ({node.id})"]
        lines.append("")
        lines.append("Properties:")
        import json

        for key in sorted(node.properties):
            if key in ("source_path", "line_start", "line_end", "confidence"):
                continue
            value = node.properties[key]
            if isinstance(value, (list, dict)):
                value = json.dumps(value) if len(json.dumps(value)) < 300 else str(value)[:300]
            lines.append(f"  {key}: {value}")
        return RichRender("\n".join(lines), self._citations(node))

    # --- building blocks ----------------------------------------------------

    @staticmethod
    def _section(title: str, items: list[str]) -> list[str]:
        if not items:
            return []
        return [f"  {title}:"] + [f"    - {item}" for item in items]

    @staticmethod
    def _source(node) -> str | None:
        path = node.properties.get("source_path", "")
        if not path:
            return None
        start = node.properties.get("line_start", 0)
        end = node.properties.get("line_end", 0)
        if start and end and start != end:
            return f"{path}:{start}-{end}"
        return f"{path}:{start}" if start else path

    def _describe_outgoing(self, node) -> list[str]:
        items = []
        for edge in self.graph._outgoing.get(node.id, []):
            target = self.graph.nodes.get(edge.target_id)
            if target:
                items.append(f"{target.label} ({target.id})")
        return items

    def _describe_incoming(self, node, exclude_tests: bool = True) -> list[str]:
        items = []
        for edge in self.graph._incoming.get(node.id, []):
            source = self.graph.nodes.get(edge.source_id)
            if source is None:
                continue
            if exclude_tests and source.id.startswith("dependency.tests."):
                continue
            if source.type == "dependency":
                imported = source.properties.get("imported_name", source.label)
                source_module = source.properties.get("source_module", "")
                items.append(f"{imported} (imported by {source_module}.py)")
            else:
                items.append(f"{source.label} ({source.id})")
        return items

    def _describe_tests(self, node) -> list[str]:
        items = []
        for edge in self.graph._incoming.get(node.id, []):
            source = self.graph.nodes.get(edge.source_id)
            if source and source.id.startswith("dependency.tests."):
                source_module = source.properties.get("source_module", source.label)
                items.append(f"{source_module} ({source.id})")
        return items

    def _describe_adrs(self, node) -> list[str]:
        items = []
        for edge in list(self.graph._outgoing.get(node.id, [])) + list(self.graph._incoming.get(node.id, [])):
            other_id = edge.target_id if edge.source_id == node.id else edge.source_id
            other = self.graph.nodes.get(other_id)
            if other and other.type == "adr":
                items.append(f"{other.label} ({other.id})")
        return items

    def _describe_milestones(self, node) -> list[str]:
        items = []
        for edge in list(self.graph._outgoing.get(node.id, [])) + list(self.graph._incoming.get(node.id, [])):
            other_id = edge.target_id if edge.source_id == node.id else edge.source_id
            other = self.graph.nodes.get(other_id)
            if other and other.type == "milestone":
                items.append(f"{other.label} ({other.id})")
        return items

    def _citations(self, node) -> list[dict]:
        return [{
            "file": node.properties.get("source_path", ""),
            "line_start": node.properties.get("line_start", 0),
            "line_end": node.properties.get("line_end", 0),
            "text": f"{node.label} - {node.type}",
            "entity_id": node.id,
        }]

    # --- purpose enrichment -------------------------------------------------

    def _purpose(self, node) -> str | None:
        path = node.properties.get("source_path", "")
        line = node.properties.get("line_start", 0)
        if not path:
            return None
        cache_key = (path, line)
        if cache_key in self._purpose_cache:
            return self._purpose_cache[cache_key]

        if path.endswith(".py"):
            purpose = self._python_docstring(path, line)
        elif path.endswith(".md"):
            purpose = self._markdown_intro(path)
        else:
            purpose = None
        self._purpose_cache[cache_key] = purpose
        return purpose

    def _python_docstring(self, path: str, line: int) -> str | None:
        try:
            import ast

            module = ast.parse(self._resolve(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return None

        best: str | None = None
        best_start = -1
        for candidate in ast.walk(module):
            if isinstance(candidate, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                start = getattr(candidate, "lineno", 0)
                if start <= line and start >= best_start:
                    doc = ast.get_docstring(candidate)
                    if doc:
                        best = doc.splitlines()[0]
                        best_start = start
        return best

    def _markdown_intro(self, path: str) -> str | None:
        try:
            text = self._resolve(path).read_text(encoding="utf-8")
        except OSError:
            return None
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("# "):
                for ln in lines[i + 1:]:
                    stripped = ln.strip()
                    if stripped and not stripped.startswith(("#", "-", "|", ">")):
                        return stripped
                return None
        return None

    def _adr_summary(self, path: str) -> str | None:
        try:
            lines = self._resolve(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        section = None
        for i, ln in enumerate(lines):
            if ln.strip().lower() in ("## context", "## summary"):
                section = i + 1
                break
        if section is None:
            return self._markdown_intro(path)
        for ln in lines[section:]:
            stripped = ln.strip()
            if stripped and not stripped.startswith(("#", "-", "|", ">")):
                return stripped
        return None

    def _domain_purpose(self, node) -> str | None:
        path = node.properties.get("source_path", "")
        line = node.properties.get("line_start", 0)
        if not path.endswith(".md"):
            return self._purpose(node)
        try:
            lines = self._resolve(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        section_start = None
        for i, ln in enumerate(lines):
            if ln.startswith("### ") and i + 1 <= line:
                section_start = i
        if section_start is None:
            return None

        for ln in lines[section_start:]:
            if "**Purpose**" in ln:
                cells = [c.strip() for c in ln.split("|")]
                if len(cells) >= 3 and cells[2]:
                    return cells[2]
        return None

    @staticmethod
    def _milestone_summary(title: str) -> str | None:
        for line in title.splitlines():
            stripped = line.strip()
            if re.match(r"^M1\.\d+ ", stripped) and len(stripped) > 12:
                return stripped
        for line in title.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("Tagger:") and not re.match(r"^\d{4}-\d{2}-\d{2}", stripped):
                return stripped
        return None
