"""Tests for deterministic profile recommendations (Platform Beta M1.1)."""

from __future__ import annotations

from typing import Any

import pytest

from careeros.reasoning import (
    ProfileRecommendation,
    ReasoningEngine,
    ReasoningReport,
    create_default_registry,
)


def _run(profile: dict[str, Any]) -> ReasoningReport:
    return ReasoningEngine(create_default_registry()).analyze(profile)


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


@pytest.fixture
def curated_profile() -> dict[str, Any]:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-strong",
            "names": [{"value": "John Strong", "usage": "professional"}],
        },
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
                "dateRange": {"start": "2018-01", "isCurrent": True},
                "scope": (
                    "Led Kubernetes and AWS infrastructure automation with Terraform, "
                    "cutting deployment time by 40%."
                ),
                "achievementRefs": [{"id": "ach-1", "type": "achievement"}],
                "skillRefs": [
                    {"id": "skill-1", "type": "skill"},
                    {"id": "skill-2", "type": "skill"},
                    {"id": "skill-3", "type": "skill"},
                ],
            }
        ],
        "organizations": [{"id": "org-1", "name": "Cloud Co"}],
        "projects": [
            {
                "id": "proj-1",
                "title": "Migration to Kubernetes",
                "skillRefs": [{"id": "skill-1", "type": "skill"}],
            }
        ],
        "skills": [
            {"id": "skill-1", "name": "Kubernetes", "category": "DevOps"},
            {"id": "skill-2", "name": "AWS", "category": "Cloud"},
            {"id": "skill-3", "name": "Terraform", "category": "DevOps"},
        ],
        "achievements": [
            {
                "id": "ach-1",
                "title": "Deployment automation",
                "description": "Cut deployment time by 40% and reduced infrastructure cost by 25%.",
                "metrics": ["40% faster deploys"],
            }
        ],
        "evidence": [],
        "education": [],
        "certifications": [
            {
                "id": "cert-1",
                "name": "AWS Certified Solutions Architect",
                "evidenceRefs": [{"id": "ev-1", "type": "evidence"}],
            }
        ],
    }


def test_weak_profile_produces_visible_recommendations(weak_profile: dict[str, Any]) -> None:
    report = _run(weak_profile)
    assert len(report.recommendations) >= 3
    finding_types = {r.finding_type for r in report.findings}
    assert "recommendation_add_measurable_achievement" in finding_types
    assert "recommendation_improve_summary" in finding_types
    assert "recommendation_remove_duplicate_skills" in finding_types


def test_curated_profile_produces_no_recommendations(curated_profile: dict[str, Any]) -> None:
    report = _run(curated_profile)
    assert report.recommendations == ()


def test_recommendations_deterministic(weak_profile: dict[str, Any]) -> None:
    first = [r.to_dict() for r in _run(weak_profile).recommendations]
    second = [r.to_dict() for r in _run(weak_profile).recommendations]
    assert first == second


def test_report_to_dict_exposes_recommendations(weak_profile: dict[str, Any]) -> None:
    payload = _run(weak_profile).to_dict()
    assert "recommendations" in payload
    assert payload["recommendations"]
    for rec in payload["recommendations"]:
        assert rec["title"]
        assert rec["reason"]
        assert rec["explanation"]
        assert rec["suggested_action"]
        assert isinstance(rec["examples"], list) and rec["examples"]
        assert rec["priority"] in ("high", "medium", "low")
        assert rec["estimated_impact"] in ("high", "medium", "low")
        assert rec["detected_pattern"]
        assert isinstance(rec["missing_information"], list) and rec["missing_information"]
        assert rec["recruiter_impact"]
        assert rec["triggered_rule"]
        assert rec["confidence"] in ("high", "medium", "low")
        assert rec["element_type"] in (None, "profile", "experience", "skill", "achievement", "project", "certification")
        assert "future_evidence" in rec


def test_weak_profile_recommendations_are_actionable(weak_profile: dict[str, Any]) -> None:
    recommendations = _run(weak_profile).recommendations
    assert len(recommendations) >= 3
    for rec in recommendations:
        assert rec.suggested_action.strip()
        assert len(rec.examples) >= 1
        assert rec.priority in ("high", "medium", "low")
        assert rec.estimated_impact in ("high", "medium", "low")


def test_weak_profile_recommendations_are_explainable(weak_profile: dict[str, Any]) -> None:
    recommendations = _run(weak_profile).recommendations
    assert len(recommendations) >= 3
    for rec in recommendations:
        assert rec.detected_pattern.strip()
        assert len(rec.missing_information) >= 1
        assert rec.recruiter_impact.strip()
        assert rec.triggered_rule.strip()


def test_recommendations_examples_are_deterministic(weak_profile: dict[str, Any]) -> None:
    first = [r.examples for r in _run(weak_profile).recommendations]
    second = [r.examples for r in _run(weak_profile).recommendations]
    assert first == second
    for examples in first:
        assert all(isinstance(ex, str) and ex.strip() for ex in examples)


def test_recommendation_model_shapes() -> None:
    rec = ProfileRecommendation(
        id="recommendation_improve_summary:profile",
        title="Add a professional summary",
        reason="reason",
        element_id=None,
        element_type="profile",
        confidence="high",
        future_evidence={"evidence_model": "not_implemented"},
        explanation="why it matters",
        suggested_action="write one",
        examples=("example one", "example two"),
        priority="high",
        estimated_impact="high",
        detected_pattern="detected",
        missing_information=("A", "B"),
        recruiter_impact="impact",
        triggered_rule="SomeRule",
    )
    d = rec.to_dict()
    assert d["confidence"] == "high"
    assert d["element_id"] is None
    assert d["future_evidence"]["evidence_model"] == "not_implemented"
    assert d["explanation"] == "why it matters"
    assert d["suggested_action"] == "write one"
    assert d["examples"] == ["example one", "example two"]
    assert d["priority"] == "high"
    assert d["estimated_impact"] == "high"
    assert d["detected_pattern"] == "detected"
    assert d["missing_information"] == ["A", "B"]
    assert d["recruiter_impact"] == "impact"
    assert d["triggered_rule"] == "SomeRule"


def test_recommendation_model_backward_compatible_defaults() -> None:
    rec = ProfileRecommendation(
        id="r1",
        title="Title",
        reason="Reason",
        element_id=None,
        element_type="profile",
        confidence="medium",
    )
    d = rec.to_dict()
    assert d["explanation"] == ""
    assert d["suggested_action"] == ""
    assert d["examples"] == []
    assert d["priority"] == "medium"
    assert d["estimated_impact"] == "medium"
    assert d["detected_pattern"] == ""
    assert d["missing_information"] == []
    assert d["recruiter_impact"] == ""
    assert d["triggered_rule"] == ""
