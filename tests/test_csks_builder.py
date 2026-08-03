"""Unit tests for the CSKS knowledge graph builder (M1.22)."""

from __future__ import annotations

from pathlib import Path

import pytest

from careeros.csks.builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from careeros.csks.models import ExtractedEntity, ExtractedRelationship
from careeros.knowledge import KnowledgeGraph


@pytest.fixture
def built_graph(csks_sample_repo: Path) -> KnowledgeGraph:
    orchestrator = CSKSExtractorOrchestrator(csks_sample_repo)
    entities, relationships = orchestrator.extract_all()
    return CSKSKnowledgeGraphBuilder().build(entities, relationships)


@pytest.fixture
def orchestrator(csks_sample_repo: Path) -> CSKSExtractorOrchestrator:
    return CSKSExtractorOrchestrator(csks_sample_repo)


def test_builder_returns_knowledge_graph(built_graph: KnowledgeGraph) -> None:
    assert isinstance(built_graph, KnowledgeGraph)
    assert built_graph.node_count > 0


def test_builder_produces_expected_types(built_graph: KnowledgeGraph) -> None:
    types = {n.type for n in built_graph.nodes.values()}
    expected = {
        "domain", "component", "rule", "generator", "api_endpoint",
        "cli_command", "dependency", "document", "adr", "schema",
        "configuration", "test", "mermaid_edge", "table_row",
    }
    assert expected <= types


def test_builder_indexes_expected_entities(built_graph: KnowledgeGraph) -> None:
    node_ids = set(built_graph.nodes)
    assert "component.careeros.profile_loader.ProfileLoader" in node_ids
    assert "rule.total_years_experience" in node_ids
    assert "generator.markdown" in node_ids
    assert "domain.profile_management" in node_ids
    assert "adr.001" in node_ids
    assert "schema.skill" in node_ids
    assert "api.get.profiles" in node_ids
    assert "cli.version" in node_ids


def test_builder_adds_domain_edges(built_graph: KnowledgeGraph) -> None:
    edges = {
        (e.source_id, e.target_id)
        for e in built_graph.edges
        if e.properties.get("type") == "domain_dependency"
    }
    assert ("domain.profile_management", "domain.schema_foundation") in edges
    assert ("domain.knowledge_graph", "domain.profile_management") in edges


def test_builder_adds_import_edges(built_graph: KnowledgeGraph) -> None:
    edges = {
        (e.source_id, e.target_id)
        for e in built_graph.edges
        if e.properties.get("type") == "import"
    }
    assert ("dependency.careeros.profile_loader.careeros.widgets.ConcreteWidget",
            "component.careeros.widgets.ConcreteWidget") in edges


def test_builder_uses_existing_knowledge_graph_class() -> None:
    import careeros.csks.builder as builder_module

    source = Path(builder_module.__file__).read_text(encoding="utf-8")
    assert "class KnowledgeGraph" not in source
    assert "KnowledgeGraph(" in source


def test_builder_drops_edges_to_missing_nodes(csks_sample_repo: Path) -> None:
    builder = CSKSKnowledgeGraphBuilder()
    entities = [
        ExtractedEntity("component", "a", {"name": "A"}, "x.py", 1, 1),
        ExtractedEntity("component", "b", {"name": "B"}, "y.py", 1, 1),
    ]
    relationships = [
        ExtractedRelationship("a", "b", "depends_on"),
        ExtractedRelationship("a", "missing", "depends_on"),
    ]
    graph = builder.build(entities, relationships)
    assert graph.node_count == 2
    assert graph.edge_count == 1
    assert graph.edges[0].target_id == "b"


def test_builder_deduplicates_duplicate_entities(csks_sample_repo: Path) -> None:
    builder = CSKSKnowledgeGraphBuilder()
    duplicate = ExtractedEntity("component", "a", {"name": "A"}, "x.py", 1, 1)
    graph = builder.build([duplicate, duplicate], [])
    assert graph.node_count == 1


def test_extractor_orchestrator_discovers_sources(orchestrator: CSKSExtractorOrchestrator) -> None:
    paths = orchestrator._discover_source_paths()
    assert "careeros/widgets.py" in paths
    assert "docs/architecture/02-domain-map.md" in paths
    assert "schemas/skill.schema.json" in paths
    assert "pyproject.toml" in paths


def test_extractor_orchestrator_excludes_vendored_dirs(orchestrator: CSKSExtractorOrchestrator) -> None:
    paths = orchestrator._discover_source_paths()
    assert not any(".venv" in p for p in paths)
    assert not any("node_modules" in p for p in paths)


def test_builder_graph_is_immutable(built_graph: KnowledgeGraph) -> None:
    snapshot = dict(built_graph.nodes)
    built_graph.nodes["bogus"] = None  # type: ignore[index]
    assert "bogus" not in built_graph.nodes
    assert built_graph.nodes == snapshot
