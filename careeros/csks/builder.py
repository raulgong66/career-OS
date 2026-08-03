from __future__ import annotations

from pathlib import Path
from typing import Iterable

from careeros.knowledge import GraphEdge, GraphNode, KnowledgeGraph

from .models import ExtractedEntity, ExtractedRelationship


class CSKSKnowledgeGraphBuilder:
    """Builds a CareerOS Self-Knowledge System graph from extracted entities and relationships.

    Reuses the existing `careeros.knowledge.KnowledgeGraph` and `GraphNode`/`GraphEdge`
    classes. CSKS entities are stored as GraphNodes with CSKS-specific types,
    and CSKS relationships as GraphEdges.
    """

    def __init__(self) -> None:
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._entity_map: dict[str, GraphNode] = {}

    def build(self, entities: Iterable, relationships: Iterable) -> KnowledgeGraph:
        """Build a KnowledgeGraph from extracted entities and relationships."""
        # First pass: add all entities as nodes
        for entity in entities:
            self._add_entity_as_node(entity)

        # Second pass: add all relationships as edges
        for relationship in relationships:
            self._add_relationship_as_edge(relationship)

        return KnowledgeGraph(self._nodes, self._edges)

    def _add_entity_as_node(self, entity) -> None:
        """Convert an ExtractedEntity to a GraphNode and add it."""
        if entity.id in self._entity_map:
            return

        node_id = entity.id

        # Use entity_type as the node type
        node_type = entity.entity_type

        # Use a label from properties or generate from ID
        label = entity.properties.get("name") or entity.properties.get("title") or entity.id.split(".")[-1]

        # Store all entity properties
        props = dict(entity.properties)
        props["source_path"] = entity.source_path
        props["line_start"] = entity.line_start
        props["line_end"] = entity.line_end
        props["confidence"] = entity.confidence

        node = GraphNode(
            id=entity.id,
            type=entity.entity_type,
            label=label,
            properties=props,
        )

        self._nodes.append(node)
        self._entity_map[entity.id] = node

    def _add_relationship_as_edge(self, relationship) -> None:
        """Convert an ExtractedRelationship to a GraphEdge and add it."""
        # Only add if both entities exist in the graph
        if relationship.from_id not in self._entity_map or relationship.to_id not in self._entity_map:
            return

        edge = GraphEdge(
            source_id=relationship.from_id,
            target_id=relationship.to_id,
            type=relationship.relationship_type,
            properties=dict(relationship.properties),
        )
        self._edges.append(edge)

    def get_graph(self) -> KnowledgeGraph:
        """Get the built KnowledgeGraph."""
        return KnowledgeGraph(self._nodes, self._edges)


class CSKSExtractorOrchestrator:
    """Orchestrates the extraction pipeline for all sources in the repository."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        from .extractor import get_all_extractors
        self.extractors = get_all_extractors(repo_root)

    def extract_all(self, source_paths: list[str] | None = None) -> tuple[list, list]:
        """Extract all entities and relationships from the repository."""
        all_entities = []
        all_relationships = []

        if source_paths is None:
            source_paths = self._discover_source_paths()

        for source_path in source_paths:
            for extractor in self.extractors:
                if extractor.can_extract(source_path):
                    try:
                        entities = list(extractor.extract_entities(source_path))
                        relationships = list(extractor.extract_relationships(source_path))
                        all_entities.extend(entities)
                        all_relationships.extend(relationships)
                    except Exception as e:
                        # Log error but continue
                        print(f"Error extracting from {source_path} with {extractor.__class__.__name__}: {e}")

        return all_entities, all_relationships

    def _discover_source_paths(self) -> list[str]:
        """Discover all source paths in the repository that should be indexed."""
        paths = []
        excluded_parts = {".git", ".venv", "venv", "__pycache__", "node_modules", ".csks-index", "dist", ".mypy_cache", ".pytest_cache"}

        def _relative(path: Path) -> str:
            rel = str(path.relative_to(self.repo_root)).replace("\\", "/")
            parts = rel.split("/")
            return rel if not excluded_parts.intersection(parts) else None

        # Python files
        for py_file in self.repo_root.rglob("*.py"):
            rel = _relative(py_file)
            if rel:
                paths.append(rel)

        # Markdown files
        for md_file in self.repo_root.rglob("*.md"):
            rel = _relative(md_file)
            if rel:
                paths.append(rel)

        # JSON Schema files
        for schema_file in self.repo_root.rglob("*.schema.json"):
            rel = _relative(schema_file)
            if rel:
                paths.append(rel)

        # Config files
        for config_file in self.repo_root.rglob("*.toml"):
            rel = _relative(config_file)
            if rel:
                paths.append(rel)
        for config_file in self.repo_root.rglob("*.yaml"):
            rel = _relative(config_file)
            if rel:
                paths.append(rel)
        for config_file in self.repo_root.rglob("*.yml"):
            rel = _relative(config_file)
            if rel:
                paths.append(rel)
        for config_file in self.repo_root.rglob(".env*"):
            rel = _relative(config_file)
            if rel:
                paths.append(rel)

        # Repo-level (git)
        paths.append(".")

        return paths