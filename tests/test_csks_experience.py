"""M1.23 developer-experience tests.

Covers the deterministic interpretation/presentation layer built on the
frozen M1.22 CSKS foundation: the query grammar, alias registry, grouped
search, rich answer formatting, milestone tag resolution, reverse
dependency, and search parity across the CLI and the REST router.

All assertions are dynamic (they use the sample-repo fixture, never
hardcoded repository-wide counts).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from careeros.csks.aliases import resolve_alias
from careeros.csks.builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from careeros.csks.cli import CSKS_APP
from careeros.csks.grammar import classify, suggest
from careeros.csks.indexer import CSKSIndexer
from careeros.csks.query import CSKSQueryEngine
from careeros.csks.rich_format import RichFormatter
from careeros.csks.search import GROUP_ORDER, grouped_search
from careeros.knowledge import GraphNode, KnowledgeGraph


@pytest.fixture
def graph(csks_sample_repo: Path) -> KnowledgeGraph:
    orchestrator = CSKSExtractorOrchestrator(csks_sample_repo)
    entities, relationships = orchestrator.extract_all()
    return CSKSKnowledgeGraphBuilder().build(entities, relationships)


@pytest.fixture
def engine(graph: KnowledgeGraph, csks_sample_repo: Path) -> CSKSQueryEngine:
    return CSKSQueryEngine(graph, repo_root=csks_sample_repo)


@pytest.fixture
def indexer(csks_sample_repo: Path) -> CSKSIndexer:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()
    return indexer


def _graph_with_documents(
    graph: KnowledgeGraph,
    csks_sample_repo: Path,
    files: dict[str, str],
    docs: list[tuple[str, str, str, int]],
) -> KnowledgeGraph:
    """Add source files plus hand-built document nodes to the sample graph."""
    for relpath, content in files.items():
        path = csks_sample_repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    nodes = list(graph.nodes.values())
    for entity_id, label, source_path, line_start in docs:
        nodes.append(GraphNode(
            entity_id,
            "document",
            label,
            {
                "title": label,
                "level": 1 if line_start == 1 else 2,
                "source_path": source_path,
                "line_start": line_start,
                "line_end": line_start,
            },
        ))
    return KnowledgeGraph(nodes, list(graph.edges))


_CAREEROS_FILES = {
    "README.md": (
        "# CareerOS\n"
        "\n"
        "CareerOS is a schema-driven toolkit for managing professional profile, application, and project data.\n"
    ),
    "docs/architecture/00-executive-summary.md": (
        "# 00 - Executive Summary\n"
        "\n"
        "## What Is CareerOS Today?\n"
        "\n"
        "CareerOS is a Python 3.11+ command-line toolkit and REST API for managing professional career data.\n"
        "\n"
        "## What Problem Does It Solve?\n"
        "\n"
        "CareerOS addresses the fragmentation of professional data across multiple formats and platforms.\n"
    ),
}

_CAREEROS_DOCS = [
    ("document.README.careeros", "CareerOS", "README.md", 1),
    (
        "document.00-executive-summary.what_is_careeros_today?",
        "What Is CareerOS Today?",
        "docs/architecture/00-executive-summary.md",
        3,
    ),
    (
        "document.00-executive-summary.what_problem_does_it_solve?",
        "What Problem Does It Solve?",
        "docs/architecture/00-executive-summary.md",
        9,
    ),
]


# --- grammar ---------------------------------------------------------------


def test_grammar_classifies_search(engine: CSKSQueryEngine) -> None:
    intent = classify("search profile")
    assert intent.query_type == "search"
    assert intent.target == "profile"


def test_grammar_classifies_reverse_dependency() -> None:
    intent = classify("What does ProfileLoader depend on?")
    assert intent.query_type == "reverse_dependency"
    assert intent.target == "ProfileLoader"


def test_grammar_rule_order_reverse_before_traversal() -> None:
    assert classify("What does ProfileLoader depend on?").query_type == "reverse_dependency"
    assert classify("What depends on ProfileLoader?").query_type == "dependency_traversal"


def test_grammar_classifies_data_flow_cv() -> None:
    intent = classify("How is a CV generated?")
    assert intent.query_type == "data_flow_path"


def test_grammar_classifies_how_applied() -> None:
    intent = classify("How is AI applied?")
    assert intent.query_type == "data_flow_path"


def test_grammar_classifies_unknown() -> None:
    assert classify("potato potato potato").query_type == "unknown"


def test_grammar_suggest_deterministic() -> None:
    first = suggest("flurble")
    second = suggest("flurble")
    assert first == second
    assert any("flurble" in item for item in first)
    assert "Search flurble." in first


def test_grammar_suggest_includes_short_tokens() -> None:
    items = suggest("AI potato")
    assert any("AI" in item for item in items)
    assert any("potato" in item for item in items)


# --- alias registry ---------------------------------------------------------


def test_alias_resolves_domain_alias() -> None:
    entry = resolve_alias("Knowledge Layer")
    assert entry is not None
    assert entry.kind == "entity"
    assert entry.entity_id == "domain.knowledge_graph"


def test_alias_folds_punctuation() -> None:
    assert resolve_alias("knowledge-layer").entity_id == "domain.knowledge_graph"
    assert resolve_alias("KNOWLEDGE_LAYER").entity_id == "domain.knowledge_graph"


def test_alias_unknown_returns_none() -> None:
    assert resolve_alias("ZzZzZzZz") is None


def test_alias_cluster_interview_intelligence() -> None:
    entry = resolve_alias("Interview Intelligence")
    assert entry is not None
    assert entry.kind == "cluster"
    assert entry.module_prefix == "careeros.interview"


def test_alias_resolves_careeros_variants() -> None:
    for alias in ("CareerOS", "careeros", "career os", "career-os", "CAREER_OS"):
        entry = resolve_alias(alias)
        assert entry is not None, alias
        assert entry.kind == "entity"
        assert entry.entity_id == "document.README.careeros"


def test_entity_lookup_knowledge_layer_alias(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is the Knowledge Layer?")
    assert result.query_type == "entity_lookup"
    assert "domain.knowledge_graph" in result.matched_entities
    assert "Domain: Knowledge Graph (domain.knowledge_graph)" in result.answer


def test_entity_lookup_interview_cluster_absent(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is Interview Intelligence?")
    assert result.query_type == "entity_lookup"
    assert result.entities_found == 0
    assert "No Interview Intelligence domain node exists" in result.answer


# --- milestone tag-prefix resolution ---------------------------------------


def _graph_with_milestone(graph: KnowledgeGraph) -> KnowledgeGraph:
    milestone = GraphNode(
        "milestone.m1.22-csks-foundation",
        "milestone",
        "M1.22 CSKS Foundation",
        {
            "tag": "m1.22-csks-foundation",
            "title": "M1.22 CSKS Foundation: deterministic knowledge graph for CareerOS",
            "status": "in_progress",
        },
    )
    return KnowledgeGraph(list(graph.nodes.values()) + [milestone], list(graph.edges))


def test_milestone_tag_prefix_resolution(graph: KnowledgeGraph) -> None:
    engine = CSKSQueryEngine(_graph_with_milestone(graph))
    result = engine.query("What is M1.22?")
    assert result.query_type == "entity_lookup"
    assert "milestone.m1.22-csks-foundation" in result.matched_entities
    assert "Milestone: m1.22-csks-foundation (milestone.m1.22-csks-foundation)" in result.answer
    assert "Status: in_progress" in result.answer
    assert "Summary: M1.22 CSKS Foundation:" in result.answer


def test_milestone_resolution_is_order_independent(graph: KnowledgeGraph) -> None:
    nodes = list(graph.nodes.values())
    milestone = GraphNode(
        "milestone.m1.22-csks-foundation",
        "milestone",
        "M1.22 CSKS Foundation",
        {"tag": "m1.22-csks-foundation", "status": "completed"},
    )
    for insertion in (0, len(nodes)):
        g = KnowledgeGraph(nodes[:insertion] + [milestone] + nodes[insertion:], list(graph.edges))
        result = CSKSQueryEngine(g).query("What is M1.22?")
        assert "milestone.m1.22-csks-foundation" in result.matched_entities


def test_entity_lookup_careeros_document(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    (csks_sample_repo / "README.md").write_text(
        "# CareerOS\n"
        "\n"
        "CareerOS is a schema-driven toolkit for managing professional profile data.\n",
        encoding="utf-8",
    )
    doc = GraphNode(
        "document.README.careeros",
        "document",
        "CareerOS",
        {
            "title": "CareerOS",
            "level": 1,
            "source_path": "README.md",
            "line_start": 1,
            "line_end": 1,
        },
    )
    g = KnowledgeGraph(list(graph.nodes.values()) + [doc], list(graph.edges))
    result = CSKSQueryEngine(g, repo_root=csks_sample_repo).query("What is CareerOS?")
    assert result.query_type == "entity_lookup"
    assert "document.README.careeros" in result.matched_entities
    assert result.confidence == 1.0
    assert len(result.citations) >= 1
    assert "schema-driven toolkit" in result.answer
    assert "Source: README.md:1" in result.answer
    assert result.answer != "Document: CareerOS (document.README.careeros)"


def test_entity_lookup_document_uses_section_intro(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    (csks_sample_repo / "docs").mkdir(exist_ok=True)
    (csks_sample_repo / "docs" / "core.md").write_text(
        "# Platform\n"
        "\n"
        "File-level intro text.\n"
        "\n"
        "## Resolution Engine\n"
        "\n"
        "Resolution Engine coordinates deterministic rule evaluation and mutation proposals.\n",
        encoding="utf-8",
    )
    doc = GraphNode(
        "document.core.resolution_engine",
        "document",
        "Resolution Engine",
        {
            "title": "Resolution Engine",
            "level": 2,
            "source_path": "docs/core.md",
            "line_start": 5,
            "line_end": 5,
        },
    )
    g = KnowledgeGraph(list(graph.nodes.values()) + [doc], list(graph.edges))
    result = CSKSQueryEngine(g, repo_root=csks_sample_repo).query("Explain the Resolution Engine")
    assert result.query_type == "entity_lookup"
    assert "document.core.resolution_engine" in result.matched_entities
    assert "coordinates deterministic rule evaluation" in result.answer
    assert "File-level intro text" not in result.answer
    assert "Details:" not in result.answer


def test_entity_lookup_document_without_source_content(graph: KnowledgeGraph) -> None:
    doc = GraphNode(
        "document.missing.source_doc",
        "document",
        "Source Doc",
        {
            "title": "Source Doc",
            "level": 1,
            "source_path": "does-not-exist.md",
            "line_start": 1,
            "line_end": 1,
        },
    )
    g = KnowledgeGraph(list(graph.nodes.values()) + [doc], list(graph.edges))
    result = CSKSQueryEngine(g).query("What is Source Doc?")
    assert result.query_type == "entity_lookup"
    assert "document.missing.source_doc" in result.matched_entities
    assert "No source summary available" in result.answer


# --- EvidencePack document lookups ------------------------------------------


def test_evidence_pack_document_lookup_with_related(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    g = _graph_with_documents(graph, csks_sample_repo, _CAREEROS_FILES, _CAREEROS_DOCS)
    engine = CSKSQueryEngine(g, repo_root=csks_sample_repo)

    result = engine.query("What is CareerOS?")
    assert result.query_type == "entity_lookup"
    assert "document.README.careeros" in result.matched_entities
    assert result.confidence == 1.0
    assert len(result.citations) >= 3
    assert "schema-driven toolkit for managing professional profile" in result.answer
    assert "Python 3.11+ command-line toolkit" in result.answer
    assert "addresses the fragmentation" in result.answer
    assert "Details:" in result.answer
    assert result.answer.index("Python 3.11+") < result.answer.index("addresses the fragmentation")

    again = engine.query("What is CareerOS?")
    assert result.answer == again.answer
    assert result.citations == again.citations


def test_evidence_pack_related_capped_at_two(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    files = dict(_CAREEROS_FILES)
    files["docs/architecture/04-support.md"] = (
        "# Architecture\n"
        "\n"
        "## CareerOS Support\n"
        "\n"
        "CareerOS supports portable artifact generation for CVs and cover letters.\n"
    )
    docs = _CAREEROS_DOCS + [
        ("document.04-support.careeros_support", "CareerOS Support", "docs/architecture/04-support.md", 3),
    ]
    engine = CSKSQueryEngine(_graph_with_documents(graph, csks_sample_repo, files, docs), repo_root=csks_sample_repo)

    result = engine.query("What is CareerOS?")
    details = [line for line in result.answer.splitlines() if line.startswith("- CareerOS")]
    assert len(details) == 2
    assert "portable artifact generation" not in result.answer
    assert len(result.citations) == 3


def test_evidence_pack_ranking_definitional_before_goal(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    files = {
        "README.md": "# CareerOS\n\nCareerOS is a schema-driven toolkit for managing professional profile data.\n",
        "docs/architecture/zzz-is.md": (
            "# Is\n"
            "\n"
            "## CareerOS Identity\n"
            "\n"
            "CareerOS is an open-source command-line toolkit for professional career data.\n"
        ),
        "docs/architecture/aaa-goal.md": (
            "# Goal\n"
            "\n"
            "## CareerOS Value\n"
            "\n"
            "CareerOS provides deterministic analysis of profile data.\n"
        ),
    }
    docs = [
        ("document.README.careeros", "CareerOS", "README.md", 1),
        ("document.zzz-is.careeros_identity", "CareerOS Identity", "docs/architecture/zzz-is.md", 3),
        ("document.aaa-goal.careeros_value", "CareerOS Value", "docs/architecture/aaa-goal.md", 3),
    ]
    engine = CSKSQueryEngine(_graph_with_documents(graph, csks_sample_repo, files, docs), repo_root=csks_sample_repo)

    result = engine.query("What is CareerOS?")
    assert result.answer.index("open-source command-line toolkit") < result.answer.index(
        "provides deterministic analysis"
    )
    assert result.citations[1].file == "docs/architecture/zzz-is.md"
    assert result.citations[2].file == "docs/architecture/aaa-goal.md"


def test_rich_formatter_does_not_select_related_evidence(graph: KnowledgeGraph, csks_sample_repo: Path) -> None:
    g = _graph_with_documents(graph, csks_sample_repo, _CAREEROS_FILES, _CAREEROS_DOCS)
    doc_node = next(n for n in g.nodes.values() if n.id == "document.README.careeros")

    render = RichFormatter(g, root=csks_sample_repo).format(doc_node)
    assert "Python 3.11+ command-line toolkit" not in render.text
    assert "Details:" not in render.text
    assert len(render.citations) == 1


# --- reverse dependency -----------------------------------------------------


def test_reverse_dependency_via_import_edges(engine: CSKSQueryEngine) -> None:
    result = engine.query("What does summarize depend on?")
    assert result.query_type == "reverse_dependency"
    assert "component.careeros.profile_loader.ProfileLoader" in result.matched_entities
    assert "depends on 1 entit(y/ies)" in result.answer


def test_reverse_dependency_unknown_target(engine: CSKSQueryEngine) -> None:
    result = engine.query("What does ZzZzZzZz depend on?")
    assert result.query_type == "reverse_dependency"
    assert result.entities_found == 0
    assert "Could not identify target entity" in result.answer


def test_reverse_dependency_same_module_imports(engine: CSKSQueryEngine) -> None:
    result = engine.query("What does load_default_profile depend on?")
    assert result.query_type == "reverse_dependency"
    assert "component.careeros.widgets.ConcreteWidget" in result.matched_entities
    assert "component.careeros.widgets.make_widget" in result.matched_entities


# --- grouped search ---------------------------------------------------------


def test_grouped_search_structure(engine: CSKSQueryEngine) -> None:
    result = grouped_search(engine.graph, "profile")
    assert result["total"] >= 1
    assert "Components" in result["groups"]
    items = result["groups"]["Components"]
    for item in items:
        assert set(item) == {"id", "type", "label", "location", "file", "line_start", "line_end"}
    assert any(item["label"] == "ProfileLoader" for item in items)


def test_grouped_search_group_order(engine: CSKSQueryEngine) -> None:
    result = grouped_search(engine.graph, "profile")
    present = [name for name in GROUP_ORDER if name in result["groups"]]
    assert present == sorted(present, key=GROUP_ORDER.index)


def test_grouped_search_deterministic(engine: CSKSQueryEngine) -> None:
    first = grouped_search(engine.graph, "profile")
    second = grouped_search(engine.graph, "profile")
    assert first == second


def test_grouped_search_no_results(engine: CSKSQueryEngine) -> None:
    result = grouped_search(engine.graph, "zzzz")
    assert result["total"] == 0
    assert result["groups"] == {}


def test_search_intent_via_engine(engine: CSKSQueryEngine) -> None:
    result = engine.query("search profile")
    assert result.query_type == "search"
    assert result.entities_found >= 1
    assert 'Search results for "profile":' in result.answer
    assert "ProfileLoader" in result.answer


def test_search_intent_no_results(engine: CSKSQueryEngine) -> None:
    result = engine.query("search zzzzzz")
    assert result.query_type == "search"
    assert result.entities_found == 0
    assert "No entities found matching" in result.answer


# --- rich formatting --------------------------------------------------------


def test_rich_format_component(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ProfileLoader?")
    assert "Component: ProfileLoader (component.careeros.profile_loader.ProfileLoader)" in result.answer
    assert "Module: careeros.profile_loader" in result.answer
    assert "Source: careeros/profile_loader.py" in result.answer
    assert "Used by:" in result.answer
    assert "imported by careeros.services.summarizer.py" in result.answer


def test_rich_format_domain(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is Profile Management?")
    assert "Domain: Profile Management (domain.profile_management)" in result.answer


def test_rich_format_adr(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ADR-008?")
    assert "adr.008" in result.matched_entities
    assert "ADR-008 (adr.008)" in result.answer
    assert "Status: Accepted" in result.answer
    assert "Summary: CSKS provides the repository knowledge graph." in result.answer

def test_rich_format_schema(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is the Skill schema?")
    assert result.query_type == "entity_lookup"
    assert "Schema: skill (schema.skill)" in result.answer


def test_rich_formatter_citations_present(engine: CSKSQueryEngine) -> None:
    render = RichFormatter(engine.graph).format(engine.graph.nodes["component.careeros.profile_loader.ProfileLoader"])
    assert render.citations
    assert render.citations[0]["entity_id"] == "component.careeros.profile_loader.ProfileLoader"


# --- unknown-query UX -------------------------------------------------------


def test_unknown_query_message_with_suggestions(engine: CSKSQueryEngine) -> None:
    result = engine.query("potato potato potato")
    assert result.query_type == "unknown"
    assert "I could not classify your query." in result.answer
    assert "Did you mean:" in result.answer


# --- determinism ------------------------------------------------------------


def test_query_deterministic(engine: CSKSQueryEngine) -> None:
    first = engine.query("What is ProfileLoader?")
    second = engine.query("What is ProfileLoader?")
    assert first.answer == second.answer
    assert first.matched_entities == second.matched_entities


# --- search parity: CLI and API ---------------------------------------------


def test_cli_search_term(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["search", "profile", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "Search results for" in result.output
    assert "ProfileLoader" in result.output
    assert "Total matches:" in result.output


def test_cli_search_no_results(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["search", "zzzzzz", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "No entities found matching" in result.output


def test_api_search_q_param(indexer: CSKSIndexer) -> None:
    from fastapi.testclient import TestClient

    from careeros.csks.api import build_csks_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(build_csks_router(indexer))
    client = TestClient(app)

    response = client.get("/csks/search", params={"q": "profile"})
    assert response.status_code == 200
    body = response.json()
    assert "groups" in body
    assert "total" in body
    assert body["total"] >= 1
    assert "Components" in body["groups"]

    faceted = client.get("/csks/search", params={"type": "domain"})
    assert faceted.status_code == 200
    fbody = faceted.json()
    assert "results" in fbody
    assert "count" in fbody
    assert fbody["count"] >= 1
    assert all(r["type"] == "domain" for r in fbody["results"])
