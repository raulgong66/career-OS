"""Unit tests for the CSKS query engine (M1.22)."""

from __future__ import annotations

from pathlib import Path

import pytest

from careeros.csks.builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from careeros.csks.query import AnswerFormatter, CSKSQueryEngine
from careeros.knowledge import KnowledgeGraph


@pytest.fixture
def graph(csks_sample_repo: Path) -> KnowledgeGraph:
    orchestrator = CSKSExtractorOrchestrator(csks_sample_repo)
    entities, relationships = orchestrator.extract_all()
    return CSKSKnowledgeGraphBuilder().build(entities, relationships)


@pytest.fixture
def engine(graph: KnowledgeGraph) -> CSKSQueryEngine:
    return CSKSQueryEngine(graph)


def test_entity_lookup(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ProfileLoader?")
    assert result.query_type == "entity_lookup"
    assert result.entities_found >= 1
    assert "component.careeros.profile_loader.ProfileLoader" in result.matched_entities
    assert result.confidence == 1.0


def test_entity_lookup_rule(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is the TotalYearsExperienceRule?")
    assert result.query_type == "entity_lookup"
    assert result.entities_found >= 1
    assert "rule.total_years_experience" in result.matched_entities


def test_entity_lookup_unknown(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is the ZzZzZzWidget?")
    assert result.entities_found == 0
    assert "Could not find entity" in result.answer


def test_entity_lookup_adr_hyphen(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ADR-001?")
    assert result.query_type == "entity_lookup"
    assert "adr.001" in result.matched_entities


def test_entity_lookup_adr_space(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ADR 001?")
    assert "adr.001" in result.matched_entities


def test_entity_lookup_adr_compact(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ADR001?")
    assert "adr.001" in result.matched_entities


def test_identifier_normalization_equivalent_forms() -> None:
    normalize = CSKSQueryEngine._normalize_identifier
    for form in ("ADR-008", "ADR 008", "ADR008", "adr.008", "adr-008", "adr 008"):
        assert normalize(form) == "adr.008"


def test_type_filter_domains(engine: CSKSQueryEngine) -> None:
    result = engine.query("List all domains")
    assert result.query_type == "type_filter"
    assert result.entities_found >= 3
    assert "domain.profile_management" in result.matched_entities


def test_type_filter_endpoints_profiles(engine: CSKSQueryEngine) -> None:
    result = engine.query("endpoints for profiles")
    assert result.query_type == "type_filter"
    assert result.entities_found >= 1
    assert "api.get.profiles" in result.matched_entities


def test_type_filter_cli_commands(engine: CSKSQueryEngine) -> None:
    result = engine.query("cli commands")
    assert result.query_type == "type_filter"
    assert result.entities_found >= 2


def test_dependency_traversal(engine: CSKSQueryEngine) -> None:
    result = engine.query("What depends on Profile Management?")
    assert result.query_type == "dependency_traversal"
    assert result.entities_found >= 1


def test_dependency_traversal_impact_via_imports(engine: CSKSQueryEngine) -> None:
    result = engine.query("What breaks if I change ProfileLoader?")
    assert result.query_type == "impact_analysis"
    assert result.entities_found >= 1
    assert any("imported by careeros.services.summarizer.py" in line for line in result.answer.splitlines())
    assert all(e.startswith("dependency.") for e in result.matched_entities)


def test_data_flow_path_artifact_generation(engine: CSKSQueryEngine) -> None:
    result = engine.query("Data flow for artifact generation")
    assert result.query_type == "data_flow_path"
    assert "1. Profile" in result.answer
    assert "Generate" in result.answer


def test_capability_check_pdf(engine: CSKSQueryEngine) -> None:
    result = engine.query("Does CareerOS support PDF generation?")
    assert result.query_type == "capability_check"
    assert "No" in result.answer


def test_capability_check_llm(engine: CSKSQueryEngine) -> None:
    result = engine.query("Does CSKS support LLM integration?")
    assert result.query_type == "capability_check"
    assert "No LLM in M1.22" in result.answer


def test_status_check(engine: CSKSQueryEngine) -> None:
    result = engine.query("M1.21 status")
    assert result.query_type == "status_check"
    assert "Completed" in result.answer


def test_unknown_query(engine: CSKSQueryEngine) -> None:
    result = engine.query("potato potato potato")
    assert result.query_type == "unknown"


def test_query_has_citations_for_lookup(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ProfileLoader?")
    assert len(result.citations) >= 1
    assert result.citations[0].file.endswith("profile_loader.py")


def test_answer_formatter_cli(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ProfileLoader?")
    text = AnswerFormatter.format_cli(result)
    assert "ProfileLoader" in text
    assert "Entities found:" in text
    assert "Query time:" in text
    assert "Confidence: 100%" in text


def test_answer_formatter_json(engine: CSKSQueryEngine) -> None:
    result = engine.query("What is ProfileLoader?")
    payload = AnswerFormatter.format_json(result)
    assert payload["answer"] != ""
    assert payload["query_type"] == "entity_lookup"
    assert payload["confidence"] == 1.0
    assert "citations" in payload


def test_extract_terms_quoted_and_numeric(engine: CSKSQueryEngine) -> None:
    terms = engine._extract_terms('"ProfileLoader" from 1999')
    assert "ProfileLoader" in terms
    assert not any(t.isdigit() for t in terms)


def test_resolve_target_prefers_component_over_dependency(engine: CSKSQueryEngine) -> None:
    node = engine._resolve_target("What is ProfileLoader?")
    assert node is not None
    assert node.type == "component"


def test_resolve_target_prefers_label_exact(engine: CSKSQueryEngine) -> None:
    node = engine._resolve_target("What is TotalYearsExperienceRule?")
    assert node is not None
    assert node.id == "rule.total_years_experience"


def test_type_filter_list_all_fallback(engine: CSKSQueryEngine) -> None:
    result = engine.query("list all widgets")
    assert result.query_type == "type_filter"
    assert result.entities_found == 0
    assert "widgets" in result.answer


def test_capability_check_unknown(engine: CSKSQueryEngine) -> None:
    result = engine.query("Does CareerOS support X-ray vision?")
    assert result.query_type == "capability_check"
    assert "Unknown capability" in result.answer


def test_status_check_unknown(engine: CSKSQueryEngine) -> None:
    result = engine.query("status of the moon")
    assert result.query_type == "status_check"
    assert "Unknown status" in result.answer


def test_dependency_traversal_unknown_target(engine: CSKSQueryEngine) -> None:
    result = engine.query("What depends on ZzZzZzUnknownThing?")
    assert result.query_type == "dependency_traversal"
    assert result.entities_found == 0


def test_dependency_traversal_no_dependents(engine: CSKSQueryEngine) -> None:
    result = engine.query("What depends on Widget?")
    assert result.query_type == "dependency_traversal"
    assert result.entities_found == 0
    assert "Nothing depends on" in result.answer


def test_find_dependents_transitive(engine: CSKSQueryEngine) -> None:
    graph = engine.graph
    from careeros.knowledge import GraphEdge, GraphNode

    nodes = [
        GraphNode("a", "component", "A", {}),
        GraphNode("b", "component", "B", {}),
        GraphNode("c", "component", "C", {}),
    ]
    edges = [
        GraphEdge("b", "a", "depends_on", {}),
        GraphEdge("c", "b", "depends_on", {}),
    ]
    sub = __import__("careeros.knowledge", fromlist=["KnowledgeGraph"]).KnowledgeGraph(nodes, edges)
    sub_engine = CSKSQueryEngine(sub)
    dependents = sub_engine._find_dependents("a")
    assert {d.id for d in dependents} == {"b", "c"}


def test_query_unknown_type(engine: CSKSQueryEngine) -> None:
    result = engine.query("potato potato")
    assert result.query_type == "unknown"
    assert result.entities_found == 0


def test_answer_formatter_empty_result(engine: CSKSQueryEngine) -> None:
    result = engine.query("potato potato")
    payload = AnswerFormatter.format_json(result)
    assert payload["query_type"] == "unknown"
    assert payload["citations"] == []
    text = AnswerFormatter.format_cli(result)
    assert "Entities found: 0" in text
