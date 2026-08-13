"""Tests for the optional Tier-3 synthesis layer (M1.25 boundary).

The layer consumes an already-validated EvidencePack and produces grounded
prose through a local AIProvider. The provider must never retrieve, browse,
or search; it receives only the question plus the bounded evidence, and every
response is re-grounded deterministically against the pack. All tests use
MockAIProvider â€” no real Ollama and no network access.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

from careeros.ai import AIError, MockAIProvider
from careeros.csks.builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from careeros.csks.concept_retrieval import ConceptRetriever
from careeros.csks.models import EvidencePack
from careeros.csks.query import CSKSQueryEngine
from careeros.csks.synthesis import (
    CSKS_SYNTHESIS_TIMEOUT,
    MAX_SYNTHESIS_EVIDENCE,
    SYNTHESIS_ENABLED_ENV,
    SynthesisEngine,
    SynthesisResult,
    build_prompt,
    citations_from_pack,
    is_synthesis_enabled,
)

QUESTION = "What is the evidence model?"


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


def _graph(repo: Path):
    orchestrator = CSKSExtractorOrchestrator(repo)
    entities, relationships = orchestrator.extract_all()
    return CSKSKnowledgeGraphBuilder().build(entities, relationships)


def _engine(repo: Path, provider=None, graph=None) -> CSKSQueryEngine:
    g = graph or _graph(repo)
    return CSKSQueryEngine(g, repo_root=repo, synthesis_provider=provider)


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SYNTHESIS_ENABLED_ENV, "true")


def _grounded(*evidence_ids: str, answer: str = "Grounded prose.", **extra) -> str:
    payload = {"status": "grounded", "answer": answer, "evidence_ids": list(evidence_ids)}
    payload.update(extra)
    return json.dumps(payload)


def _payload(prompt: str) -> dict:
    start = prompt.index('{\n  "query":')
    return json.loads(prompt[start:])


def _pack_for_question(repo: Path, question: str = QUESTION) -> EvidencePack:
    pack = ConceptRetriever(_graph(repo), repo_root=repo).retrieve(question)
    assert pack is not None
    return pack


# --------------------------------------------------------------------------
# Flag
# --------------------------------------------------------------------------


def test_synthesis_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SYNTHESIS_ENABLED_ENV, raising=False)
    assert is_synthesis_enabled() is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("", False),
    ],
)
def test_synthesis_flag_parsing(monkeypatch: pytest.MonkeyPatch, value: str, expected: bool) -> None:
    monkeypatch.setenv(SYNTHESIS_ENABLED_ENV, value)
    assert is_synthesis_enabled() is expected


# --------------------------------------------------------------------------
# (K) Default unchanged with the flag off
# --------------------------------------------------------------------------


def test_k_default_path_byte_compatible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SYNTHESIS_ENABLED_ENV, raising=False)
    repo = _concept_repo(tmp_path)
    graph = _graph(repo)

    provider = MockAIProvider()
    engine_with_provider = _engine(repo, provider=provider, graph=graph)
    engine_without_provider = CSKSQueryEngine(graph, repo_root=repo)

    with_provider = engine_with_provider.query(QUESTION)
    without_provider = engine_without_provider.query(QUESTION)

    assert provider.calls == []
    assert with_provider.answer == without_provider.answer
    assert with_provider.citations == without_provider.citations
    assert with_provider.matched_entities == without_provider.matched_entities
    assert with_provider.confidence == without_provider.confidence
    assert with_provider.entities_found == without_provider.entities_found
    assert with_provider.query_type == without_provider.query_type


# --------------------------------------------------------------------------
# (A) Qwen receives only query + evidence
# --------------------------------------------------------------------------


def test_a_provider_receives_only_query_and_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    primary_id = pack.primary.entity_id

    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(primary_id)
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    engine.query(QUESTION)

    assert len(provider.calls) == 1
    prompt = provider.calls[0]

    assert QUESTION in prompt
    payload = _payload(prompt)
    assert payload["query"] == QUESTION
    evidence_ids = {item["entity_id"] for item in payload["evidence"]}
    assert primary_id in evidence_ids
    assert all(isinstance(item["text"], str) and item["text"] for item in payload["evidence"])

    for needle in (".csks-index", "KnowledgeGraph", "browse", "tool", "repo_root", "indexer"):
        assert needle not in prompt


def test_a_evidence_ids_in_prompt_are_graph_entities(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(pack.primary.entity_id)
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    engine.query(QUESTION)

    graph = _graph(repo)
    known_ids = {node.id for node in graph.nodes.values()}
    prompt = provider.calls[0]
    payload = _payload(prompt)
    for item in payload["evidence"]:
        assert item["entity_id"] in known_ids


# --------------------------------------------------------------------------
# (B) Qwen cannot retrieve
# --------------------------------------------------------------------------


def test_b_synthesis_engine_holds_no_retrieval_inputs() -> None:
    params = list(inspect.signature(SynthesisEngine.__init__).parameters)
    assert params == ["self", "provider", "max_evidence"]


def test_b_synthesis_module_imports_no_retrieval_or_network_modules() -> None:
    import careeros.csks.synthesis as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    imports = re.findall(r"^from\s+([\w.]+)\s+import\s+.*|^import\s+([\w.]+)", source, re.M)
    imported = {part for pair in imports for part in pair if part}
    for forbidden in (
        "concept_retrieval",
        "knowledge",
        "builder",
        "indexer",
        "search",
        "extractor",
        "httpx",
        "requests",
        "urllib",
        "openai",
        "ollama",
    ):
        assert not any(name.split(".")[0] == forbidden for name in imported)


# --------------------------------------------------------------------------
# (C)/(D) Qwen cannot create evidence ids
# --------------------------------------------------------------------------


def test_c_unknown_evidence_id_rejected_by_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded("document.ghost")
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert len(provider.calls) == 1
    assert result.query_type == "concept_retrieval"
    assert "Evidence Model" in result.answer
    assert all(c.entity_id != "document.ghost" for c in result.citations)


def test_c_unknown_evidence_id_rejected_direct(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded("document.ghost")
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"
    assert "document.ghost" not in result.evidence_ids
    assert len(provider.calls) == 1


def test_d_grounded_with_empty_evidence_rejected(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(answer="Fabricated claim.")
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"
    assert result.answer != "Fabricated claim."


def test_d_grounded_with_non_string_evidence_id_rejected(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(12345)
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"


def test_d_grounded_evidence_ids_deduped(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    primary_id = pack.primary.entity_id
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(primary_id, primary_id)
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "grounded"
    assert result.evidence_ids == (primary_id,)


# --------------------------------------------------------------------------
# (E) Qwen citations ignored / rebuilt from the pack only
# --------------------------------------------------------------------------


def test_e_provider_citations_ignored_and_rebuilt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    primary_id = pack.primary.entity_id
    bogus_citations = [{"file": "/etc/passwd", "line_start": 1, "line_end": 2, "text": "bogus"}]
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(
            primary_id, citations=bogus_citations
        )
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert result.answer == "Grounded prose."
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.entity_id == primary_id
    assert citation.file == pack.primary.source_path
    assert citation.line_start == pack.primary.line_start
    assert citation.line_end == pack.primary.line_end
    assert "/etc/passwd" not in citation.file


def test_e_citations_from_pack_ignores_unknown_ids(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    citations = citations_from_pack(pack, ("document.ghost",))
    assert citations == ()


# --------------------------------------------------------------------------
# (F) No pack -> no Qwen
# --------------------------------------------------------------------------


def test_f_query_without_pack_never_invokes_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    provider = MockAIProvider(generator=lambda prompt, temperature, timeout: _grounded("whatever"))
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query("List all domains")

    assert provider.calls == []
    assert result.query_type == "type_filter"


def test_f_empty_pack_returns_insufficient_without_provider(tmp_path: Path) -> None:
    provider = MockAIProvider()
    pack = EvidencePack(query=QUESTION, primary=None, related=())

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "insufficient_evidence"
    assert provider.calls == []
    assert result.evidence_ids == ()
    assert result.confidence == 0.0


# --------------------------------------------------------------------------
# (G) Malformed JSON -> deterministic failure
# --------------------------------------------------------------------------


def test_g_malformed_json_deterministic_refusal(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(generator=lambda prompt, temperature, timeout: "not json {{{")

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"
    assert result.answer.startswith("I could not produce a grounded answer")
    assert result.confidence == 0.0


def test_g_malformed_json_engine_falls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    provider = MockAIProvider(generator=lambda prompt, temperature, timeout: "garbage")
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert len(provider.calls) == 1
    assert result.query_type == "concept_retrieval"
    assert "Evidence Model" in result.answer


# --------------------------------------------------------------------------
# (H) Refusal -> deterministic refusal
# --------------------------------------------------------------------------


def test_h_refusal_is_deterministic(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: json.dumps(
            {"status": "refusal", "answer": "I cannot help you with that.", "evidence_ids": []}
        )
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"
    assert result.answer.startswith("I could not produce a grounded answer")
    assert "I cannot help you" not in result.answer


def test_h_refusal_engine_falls_back_to_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: json.dumps(
            {"status": "refusal", "answer": "I refuse.", "evidence_ids": []}
        )
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert result.query_type == "concept_retrieval"
    assert "Evidence Model" in result.answer
    assert result.answer != "I refuse."


def test_h_unknown_status_treated_as_refusal(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: json.dumps(
            {"status": "confident", "answer": "Claim.", "evidence_ids": []}
        )
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"


# --------------------------------------------------------------------------
# (I) Valid grounded -> answer + valid evidence ids
# --------------------------------------------------------------------------


def test_i_grounded_synthesis_direct(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    primary_id = pack.primary.entity_id
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(primary_id)
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "grounded"
    assert result.answer == "Grounded prose."
    assert set(result.evidence_ids) <= {item.entity_id for item in (pack.primary, *pack.related)}
    assert result.confidence == 1.0
    assert len(provider.calls) == 1


def test_i_grounded_synthesis_through_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    ids = [pack.primary.entity_id] + [item.entity_id for item in pack.related]
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(*ids[:2])
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert result.query_type == "concept_retrieval"
    assert result.answer == "Grounded prose."
    assert result.confidence == 1.0
    assert len(result.citations) == 2
    assert tuple(c.entity_id for c in result.citations) == tuple(result.matched_entities)
    for citation in result.citations:
        assert citation.entity_id in set(ids)


# --------------------------------------------------------------------------
# (J) Confidence from retrieval, never from the model
# --------------------------------------------------------------------------


def test_j_confidence_ignores_model_confidence(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(
            pack.primary.entity_id, confidence=0.99
        )
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "grounded"
    assert result.confidence == 1.0
    assert result.confidence != 0.99


def test_j_confidence_refusal_is_zero(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(generator=lambda prompt, temperature, timeout: "garbage")

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.confidence == 0.0


# --------------------------------------------------------------------------
# (L) No external API calls
# --------------------------------------------------------------------------


def test_l_synthesis_uses_mock_provider_offline(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(generator=lambda prompt, temperature, timeout: _grounded(pack.primary.entity_id))

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "grounded"
    assert len(provider.calls) == 1


# --------------------------------------------------------------------------
# Robustness
# --------------------------------------------------------------------------


def test_provider_failure_is_deterministic_refusal(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)

    result = SynthesisEngine(MockAIProvider(fail=True)).synthesize(QUESTION, pack)

    assert result.status == "refusal"
    assert result.answer.startswith("I could not produce a grounded answer")


def test_evidence_bounded_at_max(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    items = [pack.primary] + list(pack.related)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(items[0].entity_id)
    )

    engine = SynthesisEngine(provider, max_evidence=1)
    result = engine.synthesize(QUESTION, pack)

    assert result.status == "grounded"
    prompt = provider.calls[0]
    payload = _payload(prompt)
    assert len(payload["evidence"]) == 1


def test_build_prompt_serializes_exactly_the_bounded_evidence(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    evidence = [pack.primary] + list(pack.related)

    prompt = build_prompt(QUESTION, evidence)
    payload = _payload(prompt)

    assert payload["query"] == QUESTION
    assert len(payload["evidence"]) == len(evidence)
    for item, original in zip(payload["evidence"], evidence):
        assert item["entity_id"] == original.entity_id
        assert item["text"] == original.text


def test_document_pack_synthesis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    (repo / "README.md").write_text(
        "# CareerOS\n"
        "\n"
        "## Resolution Engine\n"
        "\n"
        "The resolution engine applies reasoning rules to the knowledge graph.\n"
        "\n"
        "## Total Years Experience\n"
        "\n"
        "Total years of experience is computed by the experience rule.\n",
        encoding="utf-8",
    )
    graph = _graph(repo)
    deterministic = CSKSQueryEngine(graph, repo_root=repo).query("What is the Resolution Engine?")
    primary_id = deterministic.matched_entities[0]
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(primary_id)
    )
    _enable(monkeypatch)
    engine = CSKSQueryEngine(graph, repo_root=repo, synthesis_provider=provider)

    result = engine.query("What is the Resolution Engine?")

    assert result.query_type == "entity_lookup"
    assert result.answer == "Grounded prose."
    assert result.citations
    assert all(c.entity_id == primary_id for c in result.citations)
    assert len(provider.calls) == 1


def test_synthesis_result_is_frozen() -> None:
    import dataclasses

    result = SynthesisResult(status="refusal", answer="x", evidence_ids=(), confidence=0.0)
    assert dataclasses.is_dataclass(result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.answer = "y"


# --------------------------------------------------------------------------
# Grounding guard (Phase 6 required fix #1): concrete answer tokens must
# appear in the supplied evidence. Fail-closed.
# --------------------------------------------------------------------------


def _synthesize_grounded(tmp_path: Path, answer: str, *ids: str) -> SynthesisResult:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(
            *(ids or (pack.primary.entity_id,)), answer=answer
        )
    )
    return SynthesisEngine(provider).synthesize(QUESTION, pack)


def test_a_grounded_paraphrase_accepted(tmp_path: Path) -> None:
    result = _synthesize_grounded(
        tmp_path,
        "The evidence model explains how professional evidence is stored and verified with citations.",
    )

    assert result.status == "grounded"
    assert result.evidence_ids


def test_b_fabricated_year_rejected(tmp_path: Path) -> None:
    result = _synthesize_grounded(tmp_path, "The evidence model was introduced in 1999.")

    assert result.status == "refusal"
    assert result.evidence_ids == ()
    assert result.confidence == 0.0


def test_c_fabricated_technology_rejected(tmp_path: Path) -> None:
    result = _synthesize_grounded(tmp_path, "The evidence model uses BERT embeddings for storage.")

    assert result.status == "refusal"


def test_d_fabricated_entity_rejected(tmp_path: Path) -> None:
    result = _synthesize_grounded(tmp_path, "The evidence model is based on the Aardvark framework.")

    assert result.status == "refusal"


def test_e_valid_ids_with_unsupported_prose_rejected(tmp_path: Path) -> None:
    result = _synthesize_grounded(tmp_path, "The evidence model stores claims in a 2026 vault.")

    assert result.status == "refusal"
    assert result.evidence_ids == ()


def test_f_empty_answer_rejected(tmp_path: Path) -> None:
    result = _synthesize_grounded(tmp_path, "   ")

    assert result.status == "refusal"


def test_g_mixed_valid_and_unknown_evidence_ids_rejected(tmp_path: Path) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(
            pack.primary.entity_id, "document.ghost"
        )
    )

    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "refusal"


def test_h_grounding_rejection_falls_back_to_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded(
            pack.primary.entity_id, answer="The evidence model was introduced in 1999."
        )
    )
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert len(provider.calls) == 1
    assert result.query_type == "concept_retrieval"
    assert "Evidence Model" in result.answer
    assert "1999" not in result.answer


def test_i_valid_grounded_answer_with_supported_tokens_unchanged(tmp_path: Path) -> None:
    result = _synthesize_grounded(
        tmp_path,
        "The evidence model describes how professional evidence is stored and verified.",
    )

    assert result.status == "grounded"
    assert result.answer == "The evidence model describes how professional evidence is stored and verified."


def test_j_synthesis_disabled_byte_compat_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SYNTHESIS_ENABLED_ENV, raising=False)
    repo = _concept_repo(tmp_path)
    graph = _graph(repo)
    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded("document.ghost")
    )
    engine_with_provider = _engine(repo, provider=provider, graph=graph)
    engine_without_provider = CSKSQueryEngine(graph, repo_root=repo)

    with_provider = engine_with_provider.query(QUESTION)
    without_provider = engine_without_provider.query(QUESTION)

    assert provider.calls == []
    assert with_provider.answer == without_provider.answer
    assert with_provider.citations == without_provider.citations
    assert with_provider.matched_entities == without_provider.matched_entities
    assert with_provider.confidence == without_provider.confidence


def test_grounding_guard_tokenizer_direct(tmp_path: Path) -> None:
    from careeros.csks.synthesis import _evidence_text, _grounding_check, _grounding_tokens

    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)
    evidence = [pack.primary] + list(pack.related)

    assert "1999" in _grounding_tokens("Introduced in 1999.")
    assert "BERT" in _grounding_tokens("Uses BERT.")
    assert "careeros.csks" in _grounding_tokens("See careeros.csks.")
    assert "GPT-5" in _grounding_tokens("Based on GPT-5.")
    assert "aardvark" not in _grounding_tokens("An aardvark walked by.")

    assert _grounding_check("Evidence model", evidence) is True
    assert _grounding_check("The Aardvark model", evidence) is False
    assert _grounding_check("Introduced in 1999.", evidence) is False
    assert _evidence_text(evidence) != ""


# --------------------------------------------------------------------------
# Timeout (Phase 7): bounded provider request
# --------------------------------------------------------------------------


def test_timeout_forwarded_as_30_0(tmp_path: Path) -> None:
    """The single provider call forwards the bounded 30.0s timeout."""
    repo = _concept_repo(tmp_path)
    pack = _pack_for_question(repo)

    seen: dict[str, float] = {}

    def capture(prompt: str, temperature: float, timeout: float) -> str:
        seen["timeout"] = timeout
        return _grounded(pack.primary.entity_id)

    provider = MockAIProvider(generator=capture)
    result = SynthesisEngine(provider).synthesize(QUESTION, pack)

    assert result.status == "grounded"
    assert seen["timeout"] == 30.0
    assert seen["timeout"] == CSKS_SYNTHESIS_TIMEOUT


def test_provider_timeout_falls_back_to_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A timed-out provider call degrades to the deterministic answer."""
    repo = _concept_repo(tmp_path)

    def timed_out(prompt: str, temperature: float, timeout: float) -> str:
        raise AIError("synthesis request timed out")

    provider = MockAIProvider(generator=timed_out)
    _enable(monkeypatch)
    engine = _engine(repo, provider=provider)

    result = engine.query(QUESTION)

    assert len(provider.calls) == 1
    assert result.query_type == "concept_retrieval"
    assert "Evidence Model" in result.answer
    assert result.answer != "I could not produce a grounded answer from the supplied evidence."


def test_synthesis_disabled_byte_compatible_with_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SYNTHESIS_ENABLED_ENV, raising=False)
    repo = _concept_repo(tmp_path)
    graph = _graph(repo)

    provider = MockAIProvider(
        generator=lambda prompt, temperature, timeout: _grounded("document.ghost")
    )
    engine_with_provider = _engine(repo, provider=provider, graph=graph)
    engine_without_provider = CSKSQueryEngine(graph, repo_root=repo)

    with_provider = engine_with_provider.query(QUESTION)
    without_provider = engine_without_provider.query(QUESTION)

    assert provider.calls == []
    assert with_provider.answer == without_provider.answer
    assert with_provider.citations == without_provider.citations
    assert with_provider.matched_entities == without_provider.matched_entities
    assert with_provider.confidence == without_provider.confidence
    assert with_provider.entities_found == without_provider.entities_found
    assert with_provider.query_type == without_provider.query_type
