"""Unit tests for deterministic narrative duplicate suppression (narrative_dedup)."""

from __future__ import annotations

import copy

from careeros.export_contract import ExportContract, ExportSource
from careeros.narrative_dedup import (
    suppress_duplicate_narrative,
    _narrative_segments,
    _redundant_indices,
)


def _contract(sources: list[ExportSource], artifact_type: str = "CV") -> ExportContract:
    return ExportContract(
        profile_version="1.0.0",
        artifact_id="a1",
        artifact_type=artifact_type,
        person={"id": "p1"},
        artifact={"id": "a1"},
        sources=sources,
    )


def test_narrative_segments_extracts_text_label_fallback_for_summary() -> None:
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": "Hello world.", "label": "Summary label"}),
        ExportSource(type="experience", id="exp1", data={"scope": "Did stuff."}),
    ]
    segments = _narrative_segments(sources)
    assert len(segments) == 2
    assert segments[0]["normalized"] == "hello world."
    assert segments[1]["normalized"] == "did stuff."


def test_narrative_segments_skips_empty_and_non_narrative_sources() -> None:
    sources = [
        ExportSource(type="skill", id="sk1", data={"name": "Python"}),
        ExportSource(type="professional_summary", id="sum1", data={"text": "  "}),
    ]
    assert _narrative_segments(sources) == []


def test_exact_duplicate_across_summary_and_experience_suppresses_experience_scope() -> None:
    repeated = "Familiar with the Agile way of working and DevOps concepts."
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": repeated}),
        ExportSource(type="experience", id="exp1", data={"scope": repeated, "title": "Engineer"}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 2
    assert result.sources[0].data.get("text") == repeated
    assert result.sources[1].data.get("scope") is None
    assert result.sources[1].data.get("title") == "Engineer"
    assert result.sources[1].id == "exp1"


def test_exact_duplicate_between_two_experience_scopes_keeps_first_removes_second_scope() -> None:
    scope_text = "Managed Kubernetes clusters and CI/CD pipelines"
    sources = [
        ExportSource(type="experience", id="exp-a", data={"scope": scope_text, "title": "A"}),
        ExportSource(type="experience", id="exp-b", data={"scope": scope_text, "title": "B"}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 2
    assert result.sources[0].data.get("scope") == scope_text
    assert result.sources[1].data.get("scope") is None
    assert result.sources[1].data.get("title") == "B"


def test_subset_summary_in_summary_keeps_longer_drops_shorter() -> None:
    full = "Senior engineer with deep cloud expertise and leadership experience across global teams"
    subset = "Senior engineer with deep cloud expertise"
    sources = [
        ExportSource(type="professional_summary", id="sum-full", data={"text": full}),
        ExportSource(type="professional_summary", id="sum-sub", data={"text": subset}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 1
    assert result.sources[0].id == "sum-full"
    assert result.sources[0].data.get("text") == full


def test_experience_scope_subset_of_summary_suppressed() -> None:
    full = "Led platform engineering with Kubernetes AWS and Terraform across three regions"
    subset = "Led platform engineering with Kubernetes"
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": full}),
        ExportSource(type="experience", id="exp1", data={"scope": subset, "title": "Lead"}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 2
    assert result.sources[0].data.get("text") == full
    assert result.sources[1].data.get("scope") is None
    assert result.sources[1].data.get("title") == "Lead"


def test_unique_info_preserved_order_and_provenance_unchanged() -> None:
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": "Unique summary."}),
        ExportSource(type="experience", id="exp1", data={"scope": "Unique scope.", "title": "Dev"}),
        ExportSource(type="skill", id="sk1", data={"name": "Python"}, ref={"type": "skill"}),
    ]
    original = _contract(sources)
    result = suppress_duplicate_narrative(original)
    assert result.sources == original.sources
    assert [s.id for s in result.sources] == ["sum1", "exp1", "sk1"]
    assert result.sources[2].ref == {"type": "skill"}


def test_canonical_immutability_input_contract_sources_not_mutated() -> None:
    data_copy = {"scope": "Repeated text.", "title": "Role"}
    sources = [
        ExportSource(type="experience", id="exp1", data=copy.deepcopy(data_copy)),
    ]
    original = _contract(sources)
    original_data_snapshot = copy.deepcopy(original.sources[0].data)
    suppress_duplicate_narrative(original)
    assert original.sources[0].data == original_data_snapshot


def test_determinism_two_calls_produce_identical_contract() -> None:
    repeated = "Repeated narrative text for determinism check."
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": repeated}),
        ExportSource(type="experience", id="exp1", data={"scope": repeated}),
        ExportSource(type="experience", id="exp2", data={"scope": "Different."}),
    ]
    first = suppress_duplicate_narrative(_contract(sources))
    second = suppress_duplicate_narrative(_contract(sources))
    assert [s.id for s in first.sources] == [s.id for s in second.sources]
    for a, b in zip(first.sources, second.sources):
        assert a.data == b.data
        assert a.ref == b.ref


def test_non_cv_artifact_type_not_suppressed_by_evidence_selector() -> None:
    from careeros.evidence_selector import EvidenceSelector

    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": "Repeated."}),
        ExportSource(type="experience", id="exp1", data={"scope": "Repeated."}),
    ]
    contract = _contract(sources, artifact_type="COVER_LETTER")
    result = EvidenceSelector().select(contract)
    assert len(result.sources) == 2
    assert result.sources[1].data.get("scope") == "Repeated."


def test_exact_duplicates_three_sources_summary_and_two_experiences() -> None:
    text = "Same exact sentence repeated three times across sources"
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": text}),
        ExportSource(type="experience", id="exp1", data={"scope": text, "title": "A"}),
        ExportSource(type="experience", id="exp2", data={"scope": text, "title": "B"}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 3
    assert result.sources[0].data.get("text") == text
    # Summary is preferred keeper; exp1 and exp2 are duplicates → both have scope removed
    assert result.sources[1].data.get("scope") is None
    assert result.sources[2].data.get("scope") is None


def test_exact_duplicate_among_three_summaries_prefers_first() -> None:
    sources = [
        ExportSource(type="professional_summary", id="s1", data={"text": "Shared text."}),
        ExportSource(type="professional_summary", id="s2", data={"text": "Shared text."}),
        ExportSource(type="professional_summary", id="s3", data={"text": "Shared text."}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 1
    assert result.sources[0].id == "s1"


def test_subtitle_exp_in_summary_keeps_summary_removes_scope_only() -> None:
    summary_text = "Lead process automation initiatives using modern CI CD pipelines and Infrastructure as Code"
    scope_text = "Lead process automation"
    sources = [
        ExportSource(type="professional_summary", id="sum1", data={"text": summary_text}),
        ExportSource(type="experience", id="exp1", data={"scope": scope_text, "title": "Engineer"}),
    ]
    result = suppress_duplicate_narrative(_contract(sources))
    assert len(result.sources) == 2
    assert result.sources[0].data.get("text") == summary_text
    assert result.sources[1].data.get("scope") is None
    assert result.sources[1].data.get("title") == "Engineer"