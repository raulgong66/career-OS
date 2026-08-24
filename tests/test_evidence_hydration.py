from __future__ import annotations

from typing import Any

import yaml

from careeros.evidence_hydration import (
    build_evidence_items,
    compute_evidence_strength,
    confidence_grade,
    evidence_strength_label,
    provenance_grade,
)
from careeros.optimizer import CVOptimizer
from careeros.schema_loader import SchemaLoader
from careeros.validator import EntityValidator

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exp(
    eid: str,
    title: str,
    org_name: str,
    org_id: str,
    start: str | None = None,
    end: str | None = None,
    is_current: bool = False,
) -> dict[str, Any]:
    exp: dict[str, Any] = {
        "id": eid,
        "title": title,
    }
    dr: dict[str, Any] = {}
    if start:
        dr["start"] = start
    if end:
        dr["end"] = end
    if is_current:
        dr["isCurrent"] = True
    if dr:
        exp["dateRange"] = dr
    exp["organizationRefs"] = [{"id": org_id, "name": org_name, "type": "organization"}]
    return exp


def _skill(
    sid: str,
    name: str,
    experiences: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    skill: dict[str, Any] = {"id": sid, "name": name}
    if experiences:
        skill["extensions"] = {
            "experienceEvidence": [
                {"experienceId": e["id"]} for e in experiences
            ]
        }
    return skill


def _profile(
    skills: list[dict[str, Any]] | None = None,
    experiences: list[dict[str, Any]] | None = None,
    acquisition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    orgs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for exp in experiences or []:
        for ref in exp.get("organizationRefs", []):
            oid = ref.get("id")
            if oid and oid not in seen:
                seen.add(oid)
                orgs.append({"id": oid, "name": ref.get("name", oid)})
    profile: dict[str, Any] = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-test",
            "names": [{"value": "Test User", "usage": "professional"}],
        },
        "professionalSummaries": [],
        "experiences": experiences or [],
        "organizations": orgs,
        "projects": [],
        "skills": skills or [],
        "achievements": [],
        "evidence": [],
        "education": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
        "extensions": {},
    }
    if acquisition:
        profile["extensions"]["_acquisition"] = acquisition
    return profile


def _strong_evidence_profile(acquisition: dict[str, Any] | None = None) -> dict[str, Any]:
    exps = [
        _exp("e1", "Dev", "Corp1", "org-1", "2018-01", "2020-01"),
        _exp("e2", "Sr Dev", "Corp2", "org-2", "2020-06", "2023-01"),
        _exp("e3", "Architect", "Corp3", "org-3", "2023-06", "2026-01"),
    ]
    return _profile(
        skills=[_skill("s1", "Kubernetes", exps)],
        experiences=exps,
        acquisition=acquisition,
    )


def _validate(profile: dict[str, Any]) -> None:
    schema_loader = SchemaLoader(REPO_ROOT / "schemas")
    validator = EntityValidator(schema_loader)
    result = validator.validate_entity(profile, "profile")
    assert result.is_valid, f"Profile failed validation: {result.errors}"


# ---------------------------------------------------------------------------
# Mandatory 1: strong evidence + partial provenance
# ---------------------------------------------------------------------------


def test_strong_evidence_partial_provenance_caps_grade() -> None:
    profile = _strong_evidence_profile(
        acquisition={"sourceDocument": "resume.docx", "extractionTimestamp": "2026-01-01T00:00:00+00:00"}
    )

    items = build_evidence_items(profile)
    assert len(items) == 3

    item = items[0]
    ext = item["extensions"]
    assert ext["evidenceStrengthLabel"] == "very_high"
    assert ext["provenance"] == "partial"
    assert ext["confidenceGrade"] == "high"

    explanation = ext["provenanceExplanation"]
    assert explanation
    assert "missing: sourceHash, sourceName, importedAt" in explanation
    assert ext["basis"]
    assert item["description"] == ext["basis"]

    basis = ext["basis"]
    assert basis.startswith("Supported by ")
    assert "(" not in basis
    assert "sourceHash" not in basis
    assert "sourceName" not in basis
    assert "importedAt" not in basis

    assert "sourceHash" not in item
    assert "sourceName" not in item
    assert "importedAt" not in item
    assert "sourceHash" not in ext
    assert "sourceName" not in ext
    assert "importedAt" not in ext

    assert item["evidenceType"] == "experience"
    assert item["relatedRefs"] == [
        {"id": "s1", "type": "skill"},
        {"id": "e1", "type": "experience"},
    ]
    _validate(profile)


# ---------------------------------------------------------------------------
# Mandatory 2: strong evidence + no provenance
# ---------------------------------------------------------------------------


def test_strong_evidence_no_provenance_caps_to_medium() -> None:
    profile = _strong_evidence_profile()
    items = build_evidence_items(profile)
    assert len(items) == 3

    for item in items:
        ext = item["extensions"]
        assert ext["evidenceStrengthLabel"] == "very_high"
        assert ext["provenance"] == "none"
        assert ext["confidenceGrade"] == "medium"


def test_strong_evidence_full_provenance_not_capped() -> None:
    profile = _strong_evidence_profile(
        acquisition={
            "sourceDocument": "resume.docx",
            "sourceHash": "a" * 64,
            "sourceName": "resume.docx",
            "importedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    items = build_evidence_items(profile)
    assert items[0]["extensions"]["provenance"] == "full"
    assert items[0]["extensions"]["confidenceGrade"] == "very_high"


# ---------------------------------------------------------------------------
# Mandatory 3: thin / no evidence
# ---------------------------------------------------------------------------


def test_thin_no_evidence_produces_no_manufactured_items() -> None:
    profile = _profile(
        skills=[_skill("s1", "Kubernetes"), _skill("s2", "Azure")],
    )
    assert build_evidence_items(profile) == []

    optimizer = CVOptimizer(dict(profile))
    assert optimizer.profile["evidence"] == []


def test_thin_evidence_grade_never_high() -> None:
    profile = _profile(
        skills=[
            _skill(
                "s1",
                "Azure",
                [_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2021-01")],
            )
        ],
        experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2021-01")],
    )
    items = build_evidence_items(profile)
    assert len(items) == 1
    ext = items[0]["extensions"]
    assert ext["evidenceStrengthLabel"] in ("low", "medium")
    assert ext["confidenceGrade"] in ("medium", "low", "very_low")


# ---------------------------------------------------------------------------
# Mandatory 4: deterministic, idempotent, schema-valid
# ---------------------------------------------------------------------------


def test_hydration_deterministic_idempotent_schema_valid() -> None:
    profile = _strong_evidence_profile(
        acquisition={"sourceDocument": "resume.docx"}
    )

    items1 = build_evidence_items(profile)
    items2 = build_evidence_items(profile)
    assert items1 == items2

    profile["evidence"] = list(items1)
    items3 = build_evidence_items(profile)
    assert items3 == items1

    ids = [i["id"] for i in items1]
    assert len(ids) == len(set(ids))
    _validate(profile)


# ---------------------------------------------------------------------------
# Mandatory 5: optimizer consumes hydrated evidence
# ---------------------------------------------------------------------------


def test_optimizer_consumes_hydrated_staging_profile() -> None:
    staging = REPO_ROOT / "tests" / "fixtures" / "person-smith-profile.yaml"
    profile = yaml.safe_load(staging.read_text(encoding="utf-8"))

    items = build_evidence_items(profile)
    assert len(items) > 0
    profile["evidence"] = items

    profile["artifacts"] = [
        {
            "id": "cv-min",
            "artifactType": "CV",
            "sourceRefs": [],
        }
    ]

    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv(
        "cv-min",
        "Penetration testing engineer with Kali Linux and network security",
    )

    assert result.status.value in ("recommendations_available", "no_matches")
    assert len(result.recommendations) > 0

    rec = next(
        (r for r in result.recommendations if r.type == "skill" and "Kali" in r.display_name),
        result.recommendations[0],
    )
    assert rec.evidence
    ev = rec.evidence[0]
    assert ev.get("id", "").startswith("evidence-")
    assert ev.get("evidenceType") == "experience"
    assert ev.get("description")
    ext = ev.get("extensions") or {}
    assert ext.get("evidenceStrength") is not None
    assert ext.get("confidenceGrade") in (
        "very_low", "low", "medium", "high", "very_high",
    )
    assert ext.get("provenance") in ("full", "partial", "none")
    assert ext.get("basis")

    assert "sourceHash" not in ev
    assert "sourceHash" not in ext


def test_optimizer_genuinely_empty_profile_retains_semantics() -> None:
    canonical = REPO_ROOT / "profiles" / "raul-gongora-profile.yaml"
    profile = yaml.safe_load(canonical.read_text(encoding="utf-8"))

    assert build_evidence_items(profile) == []

    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv(
        "cv-english-source",
        "DevSecOps engineer with Kubernetes experience",
    )
    assert result.status.value in ("already_complete", "no_matches")
    assert result.recommendations == []
    assert result.summary is not None
    assert result.summary.additional_evidence == 0


# ---------------------------------------------------------------------------
# Pure confidence/provenance semantics
# ---------------------------------------------------------------------------


def test_strength_and_provenance_semantics() -> None:
    assert compute_evidence_strength(
        {"experience_count": 3, "organization_count": 3, "total_years": 7.12}
    ) == 0.85
    assert compute_evidence_strength(
        {"experience_count": 0, "organization_count": 0, "total_years": 0.0}
    ) == 0.15
    assert evidence_strength_label(0.85) == "very_high"
    assert evidence_strength_label(0.15) == "very_low"

    assert provenance_grade(None) == "none"
    assert provenance_grade({}) == "none"
    assert provenance_grade({"sourceDocument": "x"}) == "partial"
    assert provenance_grade(
        {"sourceHash": "h", "sourceName": "n", "importedAt": "t"}
    ) == "full"

    assert confidence_grade("very_high", "full") == "very_high"
    assert confidence_grade("very_high", "partial") == "high"
    assert confidence_grade("very_high", "none") == "medium"
    assert confidence_grade("low", "none") == "low"
