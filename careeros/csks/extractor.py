from __future__ import annotations

import ast
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, Iterable, Protocol

import yaml

from .models import (
    ExtractedEntity,
    ExtractedRelationship,
)


class KnowledgeExtractor(Protocol):
    """Protocol for extracting structured knowledge from a source."""

    def can_extract(self, source_path: str) -> bool:
        """Return True if this extractor can handle the given source."""
        ...

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        """Extract entities from the source."""
        ...

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        """Extract relationships from the source."""
        ...


class BaseExtractor:
    """Base class providing common extraction utilities."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def _read_file(self, source_path: str) -> str:
        """Read a file relative to repo root."""
        path = self.repo_root / source_path
        return path.read_text(encoding="utf-8")

    def _get_lines(self, source_path: str) -> list[str]:
        """Get lines of a file with line numbers."""
        content = self._read_file(source_path)
        return content.splitlines()

    def _make_citation(self, source_path: str, line_start: int, line_end: int, entity_id: str) -> dict:
        """Create a citation dict for an entity."""
        lines = self._get_lines(source_path)
        text = "\n".join(lines[line_start - 1:line_end]) if line_start <= len(lines) else ""
        return {
            "file": source_path,
            "line_start": line_start,
            "line_end": line_end,
            "text": text[:500],
            "entity_id": entity_id,
        }


class PythonASTExtractor(BaseExtractor):
    """Extracts knowledge from Python source files using AST."""

    def can_extract(self, source_path: str) -> bool:
        return source_path.endswith(".py")

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        content = self._read_file(source_path)
        try:
            tree = ast.parse(content, filename=source_path)
        except SyntaxError:
            return

        lines = self._get_lines(source_path)
        method_names = self._collect_method_names(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                yield from self._make_class_entity(node, source_path, lines)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                yield from self._make_function_entity(node, source_path, lines, method_names)
            elif isinstance(node, ast.ImportFrom):
                yield from self._make_import_entities(node, source_path, lines)
            elif isinstance(node, ast.Import):
                yield from self._make_import_entities(node, source_path, lines)

    def _classify_class(self, node: ast.ClassDef, source_path: str) -> tuple[str, str] | None:
        """Classify a class into a CSKS entity type.

        Returns ``(entity_type, entity_id)`` or ``None`` when the class is a
        generic helper that should not be indexed. Class name conventions map
        to entity types: ``*Rule`` → rule, ``*Generator`` → generator,
        otherwise component.
        """
        if source_path.startswith("tests/"):
            return "component", f"component.{self._get_module_name(source_path)}.{node.name}"
        if node.name.endswith("Rule") and node.name != "Rule":
            return "rule", f"rule.{self._camel_to_snake(node.name.removesuffix('Rule'))}"
        if node.name.endswith("Generator"):
            return "generator", f"generator.{self._camel_to_snake(node.name.removesuffix('Generator'))}"
        if source_path.startswith("careeros/reasoning/rules/"):
            return "rule", f"rule.{self._camel_to_snake(node.name.removesuffix('Rule'))}"
        return "component", f"component.{self._get_module_name(source_path)}.{node.name}"

    def _class_id(self, node: ast.ClassDef, source_path: str) -> str | None:
        """Resolve the entity ID for a class node, or ``None`` when not indexed."""
        classified = self._classify_class(node, source_path)
        return classified[1] if classified else None

    def _function_id(self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_path: str) -> str | None:
        """Resolve the entity ID for a function node, or ``None`` when not indexed.

        Functions decorated as API endpoints or CLI commands are handled by
        their decorator-driven entity types and are not component entities.
        """
        if self._make_api_endpoint_entities(node, source_path, self._get_module_name(source_path)):
            return None
        if self._make_cli_command_entities(node, source_path, self._get_module_name(source_path)):
            return None
        module = self._get_module_name(source_path)
        if source_path.startswith("tests/") and node.name.startswith("test_"):
            return f"test.{module}.{node.name}"
        return f"component.{module}.{node.name}"

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case (e.g., TotalYearsExperience → total_years_experience)."""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def _make_class_entity(self, node: ast.ClassDef, source_path: str, lines: list[str]) -> list[ExtractedEntity]:
        entity_type, entity_id = self._classify_class(node, source_path)
        props = {
            "name": node.name,
            "type": "class",
            "module": self._get_module_name(source_path),
            "bases": [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases],
            "decorators": [ast.unparse(d) for d in node.decorator_list],
            "methods": [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
            "is_protocol": any(isinstance(d, ast.Name) and d.id == "Protocol" for d in node.decorator_list),
            "is_abstract": any(isinstance(d, ast.Name) and d.id in ("abstractmethod", "ABC") for d in node.decorator_list),
        }
        return [ExtractedEntity(
            entity_type=entity_type,
            id=entity_id,
            properties=props,
            source_path=source_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )]

    def _make_function_entity(self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_path: str, lines: list[str], method_names: set[str] | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        module = self._get_module_name(source_path)

        endpoint_entities = self._make_api_endpoint_entities(node, source_path, module)
        if endpoint_entities:
            entities.extend(endpoint_entities)
            return entities

        cli_entities = self._make_cli_command_entities(node, source_path, module)
        if cli_entities:
            entities.extend(cli_entities)
            return entities

        entity_id = f"component.{module}.{node.name}"
        props = {
            "name": node.name,
            "type": "function",
            "module": module,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "decorators": [ast.unparse(d) for d in node.decorator_list],
            "args": [arg.arg for arg in node.args.args],
            "returns": ast.unparse(node.returns) if node.returns else None,
            "is_method": node.name in (method_names or set()),
        }

        if source_path.startswith("tests/") and node.name.startswith("test_"):
            entity_id = f"test.{module}.{node.name}"
            entities.append(ExtractedEntity(
                entity_type="test",
                id=entity_id,
                properties=props,
                source_path=source_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            ))
        else:
            entities.append(ExtractedEntity(
                entity_type="component",
                id=entity_id,
                properties=props,
                source_path=source_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            ))
        return entities

    def _make_api_endpoint_entities(self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_path: str, module: str) -> list[ExtractedEntity]:
        """Extract FastAPI endpoint entities from ``@app.get(...)`` style decorators."""
        entities = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "app":
                continue
            method = func.attr.upper()
            if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
                continue
            path = dec.args[0].value
            entity_id = f"api.{method.lower()}.{self._path_to_id(path)}"
            entities.append(ExtractedEntity(
                entity_type="api_endpoint",
                id=entity_id,
                properties={
                    "method": method,
                    "path": path,
                    "module": module,
                    "handler": node.name,
                },
                source_path=source_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            ))
        return entities

    def _make_cli_command_entities(self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_path: str, module: str) -> list[ExtractedEntity]:
        """Extract Typer command entities from ``@app.command("name")`` style decorators."""
        entities = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute) or func.attr != "command":
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "app":
                continue
            name = node.name
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                name = dec.args[0].value
            entities.append(ExtractedEntity(
                entity_type="cli_command",
                id=f"cli.{name}",
                properties={
                    "name": name,
                    "module": module,
                    "handler": node.name,
                },
                source_path=source_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            ))
        return entities

    @staticmethod
    def _path_to_id(path: str) -> str:
        """Convert a URL path to a deterministic slug (e.g. /profiles/{id} → profiles_id)."""
        parts = path.strip("/").split("/")
        cleaned = []
        for part in parts:
            part = part.replace("{", "").replace("}", "")
            cleaned.append(re.sub(r"[^a-zA-Z0-9_]", "_", part) or "param")
        return ".".join(cleaned)

    @staticmethod
    def _collect_method_names(tree: ast.Module) -> set[str]:
        """Collect the names of functions that are methods of a class."""
        method_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.add(child.name)
        return method_names

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        content = self._read_file(source_path)
        try:
            tree = ast.parse(content, filename=source_path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                yield from self._make_inheritance_relationships(node, source_path)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from self._make_call_relationships(node, source_path)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                yield from self._make_import_relationships(node, source_path)

    def _make_import_entities(self, node: ast.Import | ast.ImportFrom, source_path: str, lines: list[str]) -> list[ExtractedEntity]:
        entities = []
        module = self._get_module_name(source_path)
        if isinstance(node, ast.ImportFrom):
            imp_module = node.module or ""
            for alias in node.names:
                entity_id = f"dependency.{module}.{imp_module}.{alias.name}"
                entities.append(ExtractedEntity(
                    entity_type="dependency",
                    id=entity_id,
                    properties={
                        "source_module": module,
                        "imported_module": imp_module,
                        "imported_name": alias.name,
                        "alias": alias.asname,
                        "type": "from_import",
                    },
                    source_path=source_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                ))
        else:
            for alias in node.names:
                entity_id = f"dependency.{module}.{alias.name}"
                entities.append(ExtractedEntity(
                    entity_type="dependency",
                    id=entity_id,
                    properties={
                        "source_module": module,
                        "imported_module": alias.name,
                        "imported_name": alias.name,
                        "alias": alias.asname,
                        "type": "import",
                    },
                    source_path=source_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                ))
        return entities

    def _make_import_relationships(self, node: ast.Import | ast.ImportFrom, source_path: str) -> list[ExtractedRelationship]:
        """Create edges from import entities to the imported component entities.

        The dependency entity ID created in ``_make_import_entities`` is used as
        the edge source, so impact/dependency queries can find every importer of
        a component. Targets that are not represented in the graph (module-level
        imports of modules with no matching entity) are dropped by the builder.
        """
        rels = []
        module = self._get_module_name(source_path)
        if isinstance(node, ast.ImportFrom):
            imp_module = node.module or ""
            for alias in node.names:
                dep_id = f"dependency.{module}.{imp_module}.{alias.name}"
                target_id = f"component.{imp_module}.{alias.name}"
                rels.append(ExtractedRelationship(
                    from_id=dep_id,
                    to_id=target_id,
                    relationship_type="depends_on",
                    properties={"type": "import", "imported_module": imp_module, "imported_name": alias.name},
                    confidence=0.8,
                ))
        else:
            for alias in node.names:
                dep_id = f"dependency.{module}.{alias.name}"
                target_id = f"component.{alias.name}"
                rels.append(ExtractedRelationship(
                    from_id=dep_id,
                    to_id=target_id,
                    relationship_type="depends_on",
                    properties={"type": "import", "imported_module": alias.name, "imported_name": alias.name},
                    confidence=0.8,
                ))
        return rels

    def _make_inheritance_relationships(self, node: ast.ClassDef, source_path: str) -> list[ExtractedRelationship]:
        rels = []
        child_id = self._class_id(node, source_path)
        if child_id is None:
            return rels
        for base in node.bases:
            if isinstance(base, ast.Name):
                parent_id = f"component.{self._get_module_name(source_path)}.{base.id}"
                rels.append(ExtractedRelationship(
                    from_id=child_id,
                    to_id=parent_id,
                    relationship_type="depends_on",
                    properties={"type": "inheritance"},
                ))
        return rels

    def _make_call_relationships(self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_path: str) -> list[ExtractedRelationship]:
        rels = []
        caller_id = self._function_id(node, source_path)
        if caller_id is None:
            return rels
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                callee_id = f"component.{self._get_module_name(source_path)}.{n.func.id}"
                rels.append(ExtractedRelationship(
                    from_id=caller_id,
                    to_id=callee_id,
                    relationship_type="depends_on",
                    properties={"type": "function_call"},
                ))
        return rels

    def _get_module_name(self, source_path: str) -> str:
        raw = Path(source_path)
        if raw.is_absolute():
            try:
                raw = raw.relative_to(self.repo_root)
            except ValueError:
                pass
        return str(raw.with_suffix("")).replace("/", ".").replace("\\", ".")


class MarkdownExtractor(BaseExtractor):
    """Extracts knowledge from Markdown files (ADRs, specs, architecture docs)."""

    def can_extract(self, source_path: str) -> bool:
        return source_path.endswith(".md")

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        content = self._read_file(source_path)
        lines = content.splitlines()

        # Check for frontmatter
        if lines and lines[0].strip() == "---":
            yield from self._extract_frontmatter_entities(lines, source_path)

        # Extract domain entities from the domain map
        yield from self._extract_domain_entities(lines, source_path)

        # Extract ADR entities from `# ADR 0000:` headings
        yield from self._extract_adr_entities(lines, source_path)

        # Extract headings as potential entities
        yield from self._extract_heading_entities(lines, source_path)

        # Extract tables (ADR tables, spec tables)
        yield from self._extract_table_entities(lines, source_path)

        # Extract Mermaid diagrams as dependencies
        yield from self._extract_mermaid_entities(lines, source_path)

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        content = self._read_file(source_path)
        lines = content.splitlines()

        # Extract from Mermaid diagrams
        yield from self._extract_mermaid_relationships(lines, source_path)

        # Extract from tables
        yield from self._extract_table_relationships(lines, source_path)

        # Extract domain dependency edges from the domain map
        yield from self._extract_domain_relationships(lines, source_path)

    def _extract_domain_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        """Extract Domain entities from the architecture domain map."""
        entities = []
        if Path(source_path).name not in ("02-domain-map.md", "09-core-vs-modules.md"):
            return entities

        for i, line in enumerate(lines):
            match = re.match(r"^###\s+\d+\.\s+(.+)$", line.strip())
            if not match:
                continue
            name = match.group(1).strip()
            slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
            entities.append(ExtractedEntity(
                entity_type="domain",
                id=f"domain.{slug}",
                properties={"name": name, "slug": slug},
                source_path=source_path,
                line_start=i + 1,
                line_end=i + 1,
                confidence=0.9,
            ))
        return entities

    def _extract_domain_relationships(self, lines: list[str], source_path: str) -> list[ExtractedRelationship]:
        """Extract Domain dependency edges from the domain map mermaid graph."""
        rels = []
        if Path(source_path).name not in ("02-domain-map.md", "09-core-vs-modules.md"):
            return rels

        for block in self._mermaid_blocks(lines):
            aliases: dict[str, str] = {}
            for line in block:
                line = line.strip()
                if not line:
                    continue
                if "-->" in line:
                    continue
                match = re.match(r'^([A-Za-z_]+)\s*=\s*"?', line)
                if match:
                    aliases[match.group(1)] = self._domain_slug(line)
                    continue
                match = re.match(r'^([A-Za-z_]+)\s*\[', line)
                if match:
                    aliases[match.group(1)] = self._domain_slug(line)

            for line in block:
                line = line.strip()
                if "-->" not in line:
                    continue
                parts = re.split(r"\s*(-->)\s*", line)
                if len(parts) < 3:
                    continue
                source_alias = parts[0].strip()
                target_alias = parts[2].strip()
                source_slug = aliases.get(source_alias, self._domain_slug(source_alias))
                target_slug = aliases.get(target_alias, self._domain_slug(target_alias))
                if not source_slug or not target_slug or source_slug == target_slug:
                    continue
                rels.append(ExtractedRelationship(
                    from_id=f"domain.{source_slug}",
                    to_id=f"domain.{target_slug}",
                    relationship_type="depends_on",
                    properties={"type": "domain_dependency", "source": "domain_map"},
                    confidence=0.9,
                ))
        return rels

    @staticmethod
    def _domain_slug(name: str) -> str:
        # Strip node labels like `Schema["Schema Foundation<br/>schemas/"]`
        label = re.sub(r'^[A-Za-z_]+\["?', "", name)
        label = label.replace('"]', "").split("<br/>")[0].strip()
        return label.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")

    def _extract_adr_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        """Extract ADR entities from ``# ADR 0000: Title`` headings."""
        entities = []
        for i, line in enumerate(lines):
            match = re.match(r"^#\s+ADR\s+(\d+)\s*:\s*(.+)$", line.strip())
            if not match:
                continue
            number = int(match.group(1))
            title = match.group(2).strip()
            status = "Accepted"
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().lower() == "## status":
                    for k in range(j + 1, min(j + 6, len(lines))):
                        candidate = lines[k].strip()
                        if candidate:
                            status = candidate
                            break
                    break
            entities.append(ExtractedEntity(
                entity_type="adr",
                id=f"adr.{number:03d}",
                properties={"number": number, "title": title, "status": status},
                source_path=source_path,
                line_start=i + 1,
                line_end=i + 1,
                confidence=0.9,
            ))
        return entities

    @staticmethod
    def _mermaid_blocks(lines: list[str]) -> list[list[str]]:
        """Split the markdown lines into mermaid code blocks."""
        blocks: list[list[str]] = []
        in_block = False
        current: list[str] = []
        for line in lines:
            if line.strip().startswith("```mermaid"):
                in_block = True
                current = []
            elif in_block and line.strip() == "```":
                in_block = False
                blocks.append(current)
            elif in_block:
                current.append(line)
        return blocks

    def _extract_frontmatter_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        entities = []
        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            return entities

        frontmatter_text = "\n".join(lines[1:frontmatter_end])
        try:
            import yaml
            fm = yaml.safe_load(frontmatter_text)
            if not isinstance(fm, dict):
                return entities
        except Exception:
            return entities

        # Detect ADR
        if "title" in fm and "status" in fm and "number" in fm:
            adr_id = f"adr.{fm['number']:03d}"
            entities.append(ExtractedEntity(
                entity_type="adr",
                id=adr_id,
                properties={
                    "number": fm["number"],
                    "title": fm.get("title", ""),
                    "status": fm.get("status", ""),
                    "summary": fm.get("summary", ""),
                },
                source_path=source_path,
                line_start=1,
                line_end=frontmatter_end,
            ))

        # Detect milestone spec
        if "title" in fm and "version" in fm and "milestone" in fm.get("title", "").lower():
            milestone_id = f"milestone.{fm.get('number', 'unknown')}"
            entities.append(ExtractedEntity(
                entity_type="milestone",
                id=milestone_id,
                properties={
                    "number": fm.get("number", ""),
                    "title": fm.get("title", ""),
                    "status": fm.get("status", ""),
                },
                source_path=source_path,
                line_start=1,
                line_end=frontmatter_end,
            ))

        return entities

    def _extract_heading_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        entities = []
        for i, line in enumerate(lines):
            if line.startswith("# "):
                entity_id = f"document.{Path(source_path).stem}.{line[2:].strip().lower().replace(' ', '_')}"
                entities.append(ExtractedEntity(
                    entity_type="document",
                    id=entity_id,
                    properties={"title": line[2:].strip(), "level": 1},
                    source_path=source_path,
                    line_start=i + 1,
                    line_end=i + 1,
                ))
            elif line.startswith("## "):
                entity_id = f"document.{Path(source_path).stem}.{line[3:].strip().lower().replace(' ', '_')}"
                entities.append(ExtractedEntity(
                    entity_type="document",
                    id=entity_id,
                    properties={"title": line[3:].strip(), "level": 2},
                    source_path=source_path,
                    line_start=i + 1,
                    line_end=i + 1,
                ))
        return entities

    def _extract_table_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        entities = []
        in_table = False
        table_lines = []

        for i, line in enumerate(lines):
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if not in_table:
                    in_table = True
                    table_lines = [(i, line)]
                else:
                    table_lines.append((i, line))
            elif in_table:
                if table_lines:
                    entities.extend(self._parse_table(table_lines, source_path))
                in_table = False
                table_lines = []

        if in_table and table_lines:
            entities.extend(self._parse_table(table_lines, source_path))

        return entities

    def _parse_table(self, table_lines: list[tuple[int, str]], source_path: str) -> list[ExtractedEntity]:
        entities = []
        if len(table_lines) < 2:
            return entities

        headers = [h.strip() for h in table_lines[0][1].split("|")[1:-1]]
        for row_idx, (line_num, line) in enumerate(table_lines[2:], 2):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) != len(headers):
                continue

            row_data = dict(zip(headers, cells))
            entity_id = f"table_row.{Path(source_path).stem}.{table_lines[0][0]}_{row_idx}"
            entities.append(ExtractedEntity(
                entity_type="table_row",
                id=entity_id,
                properties=row_data,
                source_path=source_path,
                line_start=table_lines[0][0] + 1,
                line_end=line_num + 1,
            ))
        return entities

    def _extract_mermaid_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        entities = []
        in_mermaid = False
        mermaid_start = -1

        for i, line in enumerate(lines):
            if line.strip().startswith("```mermaid"):
                in_mermaid = True
                mermaid_start = i
            elif in_mermaid and line.strip() == "```":
                mermaid_content = "\n".join(lines[mermaid_start + 1:i])
                entities.extend(self._parse_mermaid(mermaid_content, source_path, mermaid_start + 1, i + 1))
                in_mermaid = False

        return entities

    def _parse_mermaid(self, content: str, source_path: str, start_line: int, end_line: int) -> list[ExtractedEntity]:
        entities = []
        # Simple parsing for graph TD/LR diagrams
        for line in content.splitlines():
            line = line.strip()
            if "-->" in line or "---" in line:
                # Parse A --> B or A --- B
                parts = re.split(r"\s*(-->|---)\s*", line)
                if len(parts) >= 3:
                    from_id = parts[0].strip()
                    to_id = parts[2].strip()
                    entity_id = f"mermaid.{Path(source_path).stem}.{from_id}--{to_id}"
                    yield ExtractedEntity(
                        entity_type="mermaid_edge",
                        id=entity_id,
                        properties={"from": from_id, "to": to_id, "raw": line},
                        source_path=source_path,
                        line_start=start_line,
                        line_end=end_line,
                    )
        return []

    def _extract_mermaid_relationships(self, lines: list[str], source_path: str) -> list[ExtractedRelationship]:
        rels = []
        in_mermaid = False
        mermaid_start = -1

        for i, line in enumerate(lines):
            if line.strip().startswith("```mermaid"):
                in_mermaid = True
                mermaid_start = i
            elif in_mermaid and line.strip() == "```":
                mermaid_content = "\n".join(lines[mermaid_start + 1:i])
                rels.extend(self._parse_mermaid_relationships(mermaid_content, source_path))
                in_mermaid = False

        return rels

    def _parse_mermaid_relationships(self, content: str, source_path: str) -> list[ExtractedRelationship]:
        rels = []
        for line in content.splitlines():
            line = line.strip()
            if "-->" in line:
                parts = re.split(r"\s*(-->)\s*", line)
                if len(parts) >= 3:
                    from_id = parts[0].strip()
                    to_id = parts[2].strip()
                    rels.append(ExtractedRelationship(
                        from_id=f"mermaid.{from_id}",
                        to_id=f"mermaid.{to_id}",
                        relationship_type="depends_on",
                        properties={"source": "mermaid", "raw": line},
                    ))
        return rels

    def _extract_table_relationships(self, lines: list[str], source_path: str) -> list[ExtractedRelationship]:
        # Could parse dependency tables, but complex - skip for now
        return []


class JSONSchemaExtractor(BaseExtractor):
    """Extracts knowledge from JSON Schema files."""

    def can_extract(self, source_path: str) -> bool:
        return source_path.endswith(".schema.json")

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        content = self._read_file(source_path)
        try:
            schema = json.loads(content)
        except json.JSONDecodeError:
            return

        entity_name = Path(source_path).stem.removesuffix(".schema")
        entity_id = f"schema.{entity_name}"
        props = {
            "name": entity_name,
            "title": schema.get("title", ""),
            "description": schema.get("description", ""),
            "type": schema.get("type", "object"),
            "required": schema.get("required", []),
            "properties": list(schema.get("properties", {}).keys()),
            "enum_values": {k: v.get("enum", []) for k, v in schema.get("properties", {}).items() if "enum" in v},
        }
        yield ExtractedEntity(
            entity_type="schema",
            id=f"schema.{entity_name}",
            properties=props,
            source_path=source_path,
            line_start=1,
            line_end=len(self._get_lines(source_path)),
        )

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        content = self._read_file(source_path)
        try:
            schema = json.loads(content)
        except json.JSONDecodeError:
            return

        entity_name = Path(source_path).stem.removesuffix(".schema")

        # Extract $ref dependencies
        def find_refs(obj: Any, path: str = "") -> list[str]:
            refs = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "$ref" and isinstance(v, str):
                        refs.append(v)
                    elif isinstance(v, (dict, list)):
                        refs.extend(find_refs(v, f"{path}.{k}" if path else k))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    refs.extend(find_refs(item, f"{path}[{i}]"))
            return refs

        for ref in find_refs(schema):
            if ref.startswith("#/"):
                # Internal reference - could map to another schema entity
                continue
            elif ref.startswith("./"):
                # Relative schema reference
                target = ref[2:].replace(".schema.json", "")
                yield ExtractedRelationship(
                    from_id=f"schema.{Path(source_path).stem.removesuffix('.schema')}",
                    to_id=f"schema.{target}",
                    relationship_type="depends_on",
                    properties={"type": "schema_reference", "ref": ref},
                )


class YAMLTOMLConfigExtractor(BaseExtractor):
    """Extracts knowledge from YAML, TOML, and .env configuration files."""

    def can_extract(self, source_path: str) -> bool:
        return source_path.endswith((".yaml", ".yml", ".toml", ".env", ".env.example"))

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Recursively convert non-JSON-native values to strings.

        YAML/TOML parsers can produce native ``datetime.date``/``datetime``
        scalars and other non-JSON types. Normalizing them to strings at
        extraction time keeps the extraction output JSON-native, so the
        persisted per-source artifacts round-trip without loss and incremental
        rebuilds stay identical to full rebuilds.
        """
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {key: YAMLTOMLConfigExtractor._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [YAMLTOMLConfigExtractor._json_safe(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return [YAMLTOMLConfigExtractor._json_safe(item) for item in sorted(value, key=repr)]
        return str(value)

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        content = self._read_file(source_path)
        lines = content.splitlines()

        if source_path.endswith(".toml"):
            yield from self._extract_toml_entities(content, source_path)
        elif source_path.endswith((".yaml", ".yml")):
            yield from self._extract_yaml_entities(content, source_path)
        elif source_path.endswith((".env", ".env.example")):
            yield from self._extract_env_entities(lines, source_path)

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        # Config files typically don't have explicit relationships
        return []

    def _extract_toml_entities(self, content: str, source_path: str) -> list[ExtractedEntity]:
        entities = []
        try:
            data = tomllib.loads(content)
        except Exception:
            return entities

        for section_name, section_data in data.items():
            if isinstance(section_data, dict):
                entity_id = f"configuration.{Path(source_path).stem}.{section_name}"
                yield ExtractedEntity(
                    entity_type="configuration",
                    id=entity_id,
                    properties={"section": section_name, "keys": list(section_data.keys()), "data": self._json_safe(section_data)},
                    source_path=source_path,
                    line_start=1,
                    line_end=len(self._get_lines(source_path)),
                )
            elif isinstance(section_data, list):
                entity_id = f"configuration.{Path(source_path).stem}.{section_name}"
                yield ExtractedEntity(
                    entity_type="configuration",
                    id=entity_id,
                    properties={"section": section_name, "type": "array", "items": self._json_safe(section_data)},
                    source_path=source_path,
                    line_start=1,
                    line_end=len(self._get_lines(source_path)),
                )

    def _extract_yaml_entities(self, content: str, source_path: str) -> list[ExtractedEntity]:
        entities = []
        try:
            data = yaml.safe_load(content)
        except Exception:
            return entities

        if isinstance(data, dict):
            for key, value in data.items():
                entity_id = f"configuration.{Path(source_path).stem}.{key}"
                yield ExtractedEntity(
                    entity_type="configuration",
                    id=entity_id,
                    properties={"key": key, "value_type": type(value).__name__, "value": self._json_safe(value) if not isinstance(value, (dict, list)) else str(value)[:100]},
                    source_path=source_path,
                    line_start=1,
                    line_end=len(self._get_lines(source_path)),
                )

    def _extract_env_entities(self, lines: list[str], source_path: str) -> list[ExtractedEntity]:
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                entity_id = f"configuration.{Path(source_path).stem}.{key}"
                yield ExtractedEntity(
                    entity_type="configuration",
                    id=entity_id,
                    properties={"key": key, "value": value.strip()},
                    source_path=source_path,
                    line_start=i + 1,
                    line_end=i + 1,
                )


class GitTagExtractor(BaseExtractor):
    """Extracts knowledge from Git tags and commits."""

    def can_extract(self, source_path: str) -> bool:
        # This extractor works on the repo level, not individual files
        return source_path == "." or source_path == "repo"

    def extract_entities(self, source_path: str) -> Iterable[ExtractedEntity]:
        # Get all tags
        try:
            result = subprocess.run(
                ["git", "tag", "-l", "--sort=-creatordate"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            tags = result.stdout.strip().split()
        except subprocess.CalledProcessError:
            return

        for tag in tags:
            # Get tag info
            try:
                tag_info = subprocess.run(
                    ["git", "show", "--no-patch", "--format=%ai %s", tag],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                info = tag_info.stdout.strip()
                date_str, subject = info.split(" ", 1) if " " in info else ("", info)
            except subprocess.CalledProcessError:
                date_str, subject = "", ""

            # Determine type from tag pattern
            if tag.startswith("m1.") or tag.startswith("m2."):
                entity_type = "milestone"
                entity_id = f"milestone.{tag}"
                props = {"tag": tag, "title": subject, "status": "completed", "date": date_str}
            elif tag.startswith("v"):
                entity_type = "release"
                entity_id = f"release.{tag}"
                props = {"tag": tag, "title": subject, "date": date_str}
            else:
                entity_type = "tag"
                entity_id = f"tag.{tag}"
                props = {"tag": tag, "title": subject, "date": date_str}

            yield ExtractedEntity(
                entity_type=entity_type,
                id=f"{entity_type}.{tag}",
                properties=props,
                source_path="git",
                line_start=0,
                line_end=0,
            )

    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        # Get commits and their parent relationships
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-n", "100"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            commits = result.stdout.strip().split("\n")
        except subprocess.CalledProcessError:
            return

        for commit_line in commits:
            parts = commit_line.split(" ", 1)
            if len(parts) < 2:
                continue
            commit_hash, subject = parts[0], parts[1]

            # Get parent commits
            try:
                parent_result = subprocess.run(
                    ["git", "rev-list", "--parents", "-n", "1", commit_hash],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                parents = parent_result.stdout.strip().split()
                if len(parents) > 1:
                    for parent in parents[1:]:
                        yield ExtractedRelationship(
                            from_id=f"commit.{commit_hash}",
                            to_id=f"commit.{parent}",
                            relationship_type="depends_on",
                            properties={"type": "git_parent", "subject": subject},
                        )
            except subprocess.CalledProcessError:
                pass


def get_all_extractors(repo_root: Path) -> list:
    """Get all available extractors in priority order."""
    return [
        PythonASTExtractor(repo_root),
        MarkdownExtractor(repo_root),
        JSONSchemaExtractor(repo_root),
        YAMLTOMLConfigExtractor(repo_root),
        GitTagExtractor(repo_root),
    ]