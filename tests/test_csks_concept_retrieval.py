"""Tests for deterministic concept retrieval (CSKS Tier 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from careeros.csks.builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from careeros.csks.concept_retrieval import ConceptRetriever
from careeros.csks.models import EvidencePack
from careeros.csks.query import CSKSQueryEngine
from careeros.knowledge import KnowledgeGraph


def _concept_repo(tmp_path: Path) -> Path:
    """A repo with Markdown concept documents and ADRs."""
    repo = tmp_path / "concept-repo"
    (repo / "docs" / "architecture").mkdir(parents=True)
    (repo / "docs" / "adr").mkdir(parents=True)

    (repo / "docs" / "architecture" / "01-concept.md").write_text(
        "# Concept Guide\n"
        "\n"
        "## Evidence Model\n"
        "\n"
        "The evidence model describes how professional evidence is stored and verified.\n"
        "\n"
        "## Claim Model\n"
        "\n"
        "The claim model represents statements about professional experience.\n",
        encoding="utf-8",
    )
    (repo / "docs" / "architecture" / "02-recommendations.md").write_text(
        "# Recommendations Guide\n"
        "\n"
        "## Unified Recommendations\n"
        "\n"
        "Recommendations are generated from profile quality findings.\n",
        encoding="utf-8",
    )
    (repo / "docs" / "adr" / "0003-evidence.md").write_text(
        "# ADR 0003: Evidence Storage\n"
        "\n"
        "## Context\n"
        "\n"
        "Professional evidence must be verifiable and citation backed.\n"
        "\n"
        "## Decision\n"
        "\n"
        "Use the evidence model with explicit citations.\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["."]\n',
        encoding="utf-8",
    )
    return repo


@pytest.fixture
def concept_graph(tmp_path: Path) -> tuple[KnowledgeGraph, Path]:
    repo = _concept_repo(tmp_path)
    orchestrator = CSKSExtractorOrchestrator(repo)
    entities, relationships = orchestrator.extract_all()
    graph = CSKSKnowledgeGraphBuilder().build(entities, relationships)
    return graph, repo


def _engine(graph: KnowledgeGraph, repo: Path) -> CSKSQueryEngine:
    return CSKSQueryEngine(graph, repo_root=repo)


def test_concept_retrieval_answers_concept_question(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("What is the evidence model?")
    assert result.query_type == "concept_retrieval"
    assert result.confidence == 1.0
    assert result.entities_found >= 1
    assert any("evidence" in c.text.lower() or "evidence" in c.file.lower() for c in result.citations)
    assert "Evidence Model" in result.answer


def test_concept_retrieval_primary_is_authoritative(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    pack = ConceptRetriever(graph, repo_root=repo).retrieve("What is the evidence model?")
    assert pack is not None
    assert pack.primary is not None
    assert pack.primary.role == "primary"
    assert pack.primary.source_path.endswith("01-concept.md")
    assert pack.retrieval_layer == "deterministic_concept"
    assert pack.retrieval_score is not None
    assert pack.retrieval_score >= 2.5


def test_evidence_pack_related_capped(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    pack = ConceptRetriever(graph, repo_root=repo).retrieve("What is the evidence model?")
    assert pack is not None
    assert len(pack.related) <= 2
    assert len(pack.related) + 1 <= 3


def test_evidence_pack_deduplicates(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    pack = ConceptRetriever(graph, repo_root=repo).retrieve("What is the evidence model?")
    assert pack is not None
    keys = [(p.source_path, p.text) for p in (pack.primary, *pack.related)]
    assert len(keys) == len(set(keys))


def test_concept_retrieval_rejects_weak_match(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("What is the purple monkey?")
    assert result.confidence == 0.0
    assert result.entities_found == 0
    assert not result.citations


def test_concept_retrieval_deterministic(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    engine = _engine(graph, repo)
    first = engine.query("What is the evidence model?")
    second = engine.query("What is the evidence model?")
    assert first.answer == second.answer
    assert first.citations == second.citations


def test_concept_retrieval_citations_resolve_to_files(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("What is the evidence model?")
    for citation in result.citations:
        source = repo / citation.file
        assert source.is_file(), citation.file
        lines = source.read_text(encoding="utf-8").splitlines()
        assert 1 <= citation.line_start <= len(lines), (citation.file, citation.line_start)


def test_concept_retrieval_adr_full_text(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("How is evidence stored?")
    assert result.query_type == "concept_retrieval"
    assert any("adr" in c.file for c in result.citations)


def test_strong_lookup_bypasses_concept_fallback(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("What is the Claim Model?")
    assert result.query_type in ("entity_lookup", "concept_retrieval")
    assert result.confidence == 1.0


def test_recommendations_flow_not_unknown_data_flow(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("How are recommendations generated?")
    assert result.query_type == "data_flow_path"
    assert "Data flow for recommendations" in result.answer
    assert "Unified Recommendations" in result.answer


def test_profile_quality_without_profile_keeps_message(concept_graph: tuple[KnowledgeGraph, Path]) -> None:
    graph, repo = concept_graph
    result = _engine(graph, repo).query("How are duplicate narratives detected?")
    assert result.query_type == "profile_quality_check"
    assert "No profile is attached" in result.answer


def test_evidence_pack_default_metadata() -> None:
    pack = EvidencePack(query="x", primary=None)
    assert pack.retrieval_layer is None
    assert pack.retrieval_score is None
