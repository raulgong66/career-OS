"""Tests for the Profile Quality Engine (Platform Beta M1.24.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from careeros.knowledge import KnowledgeGraph, KnowledgeGraphBuilder
from careeros.profile_quality import (
    DIMENSION_WEIGHTS,
    HEALTH_DIMENSIONS,
    ProfileQualityEngine,
    ProfileQualityReport,
    RULE_ID_TO_DIMENSION,
    UnifiedRecommendation,
    health_dimensions,
    resolution_type_for_rule,
    run_profile_quality,
    to_unified_recommendations,
)
from careeros.reasoning import Rule, create_default_registry
from careeros_cli.main import app

SAMPLE_PROFILE = (
    Path(__file__).resolve().parents[1] / "profiles" / "raul-gongora-profile.yaml"
)

runner = CliRunner()


@pytest.fixture
def sample_profile() -> dict[str, Any]:
    return yaml.safe_load(SAMPLE_PROFILE.read_text(encoding="utf-8"))


@pytest.fixture
def strong_profile() -> dict[str, Any]:
    return {
        "profileVersion": "1.0.0",
        "person": {"id": "person-strong", "names": [{"value": "John Strong"}]},
        "professionalSummaries": [
            {
                "id": "sum-1",
                "text": (
                    "Senior DevOps engineer with 8 years scaling AWS platforms; cut "
                    "deployment time by 40% and improved uptime to 99.9%."
                ),
            }
        ],
        "experiences": [
            {
                "id": "exp-1",
                "title": "Senior DevOps Engineer",
                "organizationRefs": [{"id": "org-1", "type": "organization"}],
                "dateRange": {"start": "2020-01", "isCurrent": True},
                "scope": (
                    "Automated AWS infrastructure with Python and Kubernetes; "
                    "reduced deployment time by 40%."
                ),
                "achievementRefs": [
                    {"id": "ach-1", "type": "achievement"}
                ],
            }
        ],
        "organizations": [{"id": "org-1", "name": "Acme Cloud"}],
        "projects": [
            {
                "id": "proj-1",
                "title": "Migration Platform",
                "description": "A platform.",
                "skillRefs": [{"id": "skill-1", "type": "skill"}],
                "experienceRefs": [{"id": "exp-1", "type": "experience"}],
            }
        ],
        "skills": [
            {
                "id": "skill-1",
                "name": "Python",
                "category": "Programming Language",
                "extensions": {"experienceEvidence": [{"experienceId": "exp-1"}]},
            }
        ],
        "achievements": [
            {
                "id": "ach-1",
                "title": "Cut deployment time",
                "statement": "Reduced deployment time by 40%.",
                "metrics": ["40%"],
            }
        ],
        "certifications": [
            {"id": "cert-1", "name": "AWS Solutions Architect", "evidenceRefs": ["exp-1"]}
        ],
        "evidence": [],
        "education": [],
    }


@pytest.fixture
def weak_profile() -> dict[str, Any]:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-weak",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
        },
        "professionalSummaries": [],
        "experiences": [
            {
                "id": "exp-1",
                "title": "Software Engineer",
                "organizationRefs": [{"id": "org-1", "type": "organization"}],
                "dateRange": {"start": "2020-01", "isCurrent": True},
                "scope": "Responsible for developing and maintaining software applications.",
            }
        ],
        "organizations": [{"id": "org-1", "name": "Test Company"}],
        "projects": [
            {"id": "proj-1", "title": "Internal Dashboard", "description": "A dashboard."}
        ],
        "skills": [
            {"id": "skill-1", "name": "Python", "category": "Programming Language"},
            {"id": "skill-2", "name": "python", "category": "Programming Language"},
        ],
        "achievements": [
            {
                "id": "ach-1",
                "title": "Built monitoring",
                "description": "Set up dashboards for the platform.",
            }
        ],
        "evidence": [],
        "education": [],
        "certifications": [
            {"id": "cert-1", "name": "AWS Certified Solutions Architect"}
        ],
    }


def test_report_shape(sample_profile: dict[str, Any]) -> None:
    """AC 1.1: report exposes the expected, spec-compliant structure."""
    report = run_profile_quality(sample_profile)

    assert isinstance(report, ProfileQualityReport)
    assert isinstance(report.health_score, int)
    assert 0 <= report.health_score <= 100

    dimension_names = [dimension.name for dimension in report.dimension_scores]
    assert dimension_names == list(HEALTH_DIMENSIONS)
    assert len(report.dimension_scores) == 8

    for dimension in report.dimension_scores:
        assert dimension.weight == DIMENSION_WEIGHTS[dimension.name]
        assert 0.0 <= dimension.score <= 1.0

    assert report.findings
    assert report.citations
    for finding in report.findings:
        assert finding.citations, "every finding must cite evidence"
        assert finding.dimension == RULE_ID_TO_DIMENSION[finding.rule_id]
        assert finding.resolution_type in {"auto", "guided"}
        assert finding.priority in {"high", "medium", "low"}

    assert report.profile_id == "person-raul-gongora"
    assert report.profile_version == "1.0.0"


def test_determinism_100_runs(sample_profile: dict[str, Any]) -> None:
    """AC 1.2: the same profile always yields identical analysis output.

    ``generated_at`` is metadata (run timestamp) and is excluded from the
    determinism contract; all computed content must be byte-identical.
    """
    first = _analysis_payload(run_profile_quality(sample_profile))
    for _ in range(100):
        assert _analysis_payload(run_profile_quality(sample_profile)) == first


def _analysis_payload(report: ProfileQualityReport) -> dict[str, Any]:
    payload = report.to_dict()
    payload.pop("generated_at", None)
    return payload


def test_citations_for_non_perfect_dimensions(sample_profile: dict[str, Any]) -> None:
    """AC 1.3: every non-perfect dimension cites its evidence."""
    report = run_profile_quality(sample_profile)
    for dimension in report.dimension_scores:
        if dimension.score < 1.0:
            assert dimension.citations, (
                f"dimension {dimension.name} scored {dimension.score} but has no citations"
            )


def test_rule_to_dimension_mapping_is_verified() -> None:
    """AC 1.4: every mapping key is a live registry rule and a valid dimension."""
    registry = create_default_registry()
    live_rule_ids = {rule.id for rule in registry.execution_order()}

    assert set(RULE_ID_TO_DIMENSION) <= live_rule_ids
    assert set(RULE_ID_TO_DIMENSION.values()) <= set(HEALTH_DIMENSIONS)
    assert len(RULE_ID_TO_DIMENSION) == 8


def test_registry_is_reused(sample_profile: dict[str, Any]) -> None:
    """AC 1.5: the facade reuses the reasoning registry; no rule duplication."""
    engine = ProfileQualityEngine()
    default = create_default_registry()
    assert [rule.id for rule in engine.registry.execution_order()] == [
        rule.id for rule in default.execution_order()
    ]
    report = engine.run(sample_profile)
    assert report.health_score >= 0


def test_resolution_types() -> None:
    """AC 1.6 / ADR-009: resolution type derives from the Resolution Engine."""
    auto_ids = {
        "recommendation_add_measurable_achievement",
        "recommendation_show_skill_in_experience",
        "recommendation_add_technologies",
        "recommendation_add_skills_to_project",
    }
    for rule_id in RULE_ID_TO_DIMENSION:
        expected = "auto" if rule_id in auto_ids else "guided"
        assert resolution_type_for_rule(rule_id) == expected


def test_findings_resolution_type_consistency(sample_profile: dict[str, Any]) -> None:
    report = run_profile_quality(sample_profile)
    for finding in report.findings:
        assert finding.resolution_type == resolution_type_for_rule(finding.rule_id)


def test_health_dimension_descriptors() -> None:
    descriptors = health_dimensions()
    assert [dimension.name for dimension in descriptors] == list(HEALTH_DIMENSIONS)
    assert sum(dimension.weight for dimension in descriptors) == pytest.approx(1.0)


def test_strong_profile_scores_full_mark(strong_profile: dict[str, Any]) -> None:
    """A fully evidenced profile scores 100 with no findings."""
    report = run_profile_quality(strong_profile)
    assert report.health_score == 100
    assert report.findings == ()
    assert report.dimension_scores[0].name == "achievement_measurability"
    assert all(dimension.score == 1.0 for dimension in report.dimension_scores)


def test_weak_profile_flags_all_dimensions(weak_profile: dict[str, Any]) -> None:
    """An empty profile yields findings across dimensions and a low score."""
    report = run_profile_quality(weak_profile)
    assert report.health_score < 100
    assert len(report.findings) >= 7
    rule_ids = {finding.rule_id for finding in report.findings}
    assert {
        "recommendation_improve_summary",
        "recommendation_add_measurable_achievement",
        "recommendation_add_technologies",
        "recommendation_show_skill_in_experience",
        "recommendation_remove_duplicate_skills",
        "recommendation_add_business_outcome",
        "recommendation_show_certification_value",
        "recommendation_add_skills_to_project",
    } <= rule_ids


def test_empty_profile_only_missing_summary() -> None:
    """A profile with empty sections scores 90: vacuous dimensions are perfect,
    but a missing professional summary is flagged (spec SS3.4, GenericSummaryRule)."""
    profile: dict[str, Any] = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-empty"},
        "professionalSummaries": [],
        "experiences": [],
        "projects": [],
        "skills": [],
        "achievements": [],
        "certifications": [],
        "education": [],
    }
    report = run_profile_quality(profile)
    assert report.health_score == 90
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.rule_id == "recommendation_improve_summary"
    assert finding.title == "Add a professional summary"
    assert report.profile_id == "person-empty"


def test_unified_recommendations(sample_profile: dict[str, Any]) -> None:
    """ADR-009: findings normalize into unified recommendations."""
    report = run_profile_quality(sample_profile)
    recommendations = to_unified_recommendations(report)

    assert recommendations
    for rec in recommendations:
        assert isinstance(rec, UnifiedRecommendation)
        assert rec.source == "profile_quality"
        assert rec.resolution_type in {"auto", "guided"}
        assert rec.rule_id in RULE_ID_TO_DIMENSION
        assert rec.element_id
        assert rec.title

    keys = {(rec.rule_id, rec.element_id) for rec in recommendations}
    assert len(keys) == len(recommendations), "recommendations must be deduplicated"


def test_unified_recommendations_optimization_merge(sample_profile: dict[str, Any]) -> None:
    """ADR-009 dedup: profile_quality wins on (rule_id, element_id) conflict."""
    report = run_profile_quality(sample_profile)
    first = report.findings[0]

    class FakeRecommendation:
        def __init__(self, rec_id: str, rec_type: str, name: str) -> None:
            self.id = rec_id
            self.type = rec_type
            self.operation = "ADD"
            self.display_name = name
            self.details = {"detail": "x"}
            self.evidence = [{"id": "ev-1", "title": "Evidence"}]
            self.scores = {
                "job_description_match": 0.8,
                "target_context_match": 0.7,
                "weighted_total": 0.75,
            }

    class FakeResult:
        recommendations = [
            FakeRecommendation(first.element_id, first.rule_id, "Conflict"),
            FakeRecommendation("proj-9", "project", "Extra suggestion"),
        ]

    recommendations = to_unified_recommendations(report, FakeResult())

    sources = {
        (rec.rule_id, rec.element_id): rec.source for rec in recommendations
    }
    assert sources[(first.rule_id, first.element_id)] == "profile_quality"

    extra = next(
        rec
        for rec in recommendations
        if rec.element_id == "proj-9" and rec.source == "optimization"
    )
    assert extra.jd_match_score == 0.8
    assert extra.context_match_score == 0.7
    assert extra.weighted_total == 0.75
    assert extra.evidence_refs == ["ev-1"]
    assert extra.resolution_type == "none"


def test_duplicate_entity_ids_do_not_crash_health_analysis() -> None:
    """Regression: repeated education ids raised a ``Duplicate node ID``
    ValueError that surfaced as an HTTP 500 on the quality-report endpoint.
    """
    from careeros.profile_quality.cli import profile_health_data

    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-dup", "names": [{"value": "Jane Doe"}]},
        "professionalSummaries": [],
        "experiences": [
            {
                "id": "exp-1",
                "title": "Engineer",
                "organizationRefs": [{"id": "org-1", "type": "organization"}],
                "dateRange": {"start": "2020-01", "isCurrent": True},
            }
        ],
        "organizations": [{"id": "org-1", "name": "Acme"}],
        "projects": [],
        "skills": [],
        "achievements": [],
        "evidence": [],
        "education": [
            {
                "id": "edu-dup",
                "program": "Bachelor's in commerce",
                "institutionRef": {"id": "org-uni", "type": "organization"},
                "dateRange": {"start": "1998-09", "end": "2002-06"},
            },
            {
                "id": "edu-dup",
                "program": "Bachelor's in commerce",
                "institutionRef": {"id": "org-uni", "type": "organization"},
                "dateRange": {"start": "1998-08", "end": "2016-06"},
            },
        ],
        "certifications": [],
    }
    report = run_profile_quality(profile)
    assert report.health_score is not None
    data = profile_health_data(profile)
    assert "health_score" in data


def test_no_parallel_knowledge_graph(sample_profile: dict[str, Any]) -> None:
    """AC 1.11: the facade builds the knowledge graph exactly once per run."""
    calls: list[Any] = []
    original_build = KnowledgeGraphBuilder.build

    def counting_build(self: Any, profile: dict[str, Any]) -> KnowledgeGraph:
        calls.append(profile)
        return original_build(self, profile)

    try:
        KnowledgeGraphBuilder.build = counting_build
        ProfileQualityEngine().run(sample_profile)
    finally:
        KnowledgeGraphBuilder.build = original_build

    assert len(calls) == 1


def test_cli_profile_health(sample_profile: dict[str, Any]) -> None:
    """AC 3.2: CLI profile-health returns the JSON report."""
    result = runner.invoke(app, ["profile-health", str(SAMPLE_PROFILE)])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data["health_score"], int)
    assert len(data["dimensions"]) == 8
    assert data["citations"]


def test_cli_improvement_queue(sample_profile: dict[str, Any]) -> None:
    """AC 3.2: CLI improvement-queue returns unified recommendations."""
    result = runner.invoke(
        app, ["improvement-queue", str(SAMPLE_PROFILE), "--resolution", "auto"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data, "expected at least one auto-resolvable recommendation"
    for rec in data:
        assert rec["source"] == "profile_quality"
        assert rec["resolution_type"] == "auto"


def test_imports_do_not_duplicate_rules() -> None:
    """AC 1.5 companion: profile_quality defines no new Rule classes."""
    from careeros import profile_quality

    for name in dir(profile_quality):
        obj = getattr(profile_quality, name)
        if isinstance(obj, type) and issubclass(obj, Rule) and obj is not Rule:
            raise AssertionError(f"profile_quality must not define rules, got {name}")
