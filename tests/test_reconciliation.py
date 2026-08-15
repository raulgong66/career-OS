"""Unit tests for deterministic Phase 3A profile reconciliation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from careeros.reconciliation import (
    EntityDiffType,
    ProvenanceWarningType,
    _compare_entities,
    _extract_provenance_warnings,
    reconcile_profiles,
)


def _record(profile_id: str, data: dict) -> SimpleNamespace:
    return SimpleNamespace(profile_id=profile_id, data=data)


def _person(
    pid: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    linkedin: str | None = None,
    github: str | None = None,
) -> dict:
    person: dict = {"id": pid}
    if name:
        person["names"] = [{"value": name, "usage": "professional"}]
    contact: dict = {}
    if email:
        contact["email"] = email
    if phone:
        contact["phone"] = phone
    if contact:
        person["contact"] = contact
    if linkedin or github:
        links = []
        if linkedin:
            links.append({"label": "LinkedIn", "href": linkedin})
        if github:
            links.append({"label": "GitHub", "href": github})
        person["links"] = links
    return person


def _profile(
    pid: str,
    person: dict | None = None,
    experiences: list[dict] | None = None,
    organizations: list[dict] | None = None,
    skills: list[dict] | None = None,
    education: list[dict] | None = None,
    certifications: list[dict] | None = None,
    projects: list[dict] | None = None,
    achievements: list[dict] | None = None,
    evidence: list[dict] | None = None,
    artifacts: list[dict] | None = None,
    targetContexts: list[dict] | None = None,
    professionalSummaries: list[dict] | None = None,
    source_hash: str | None = None,
    source_name: str | None = None,
    imported_at: str | None = None,
) -> dict:
    data: dict = {
        "profileVersion": "1.0.0",
        "person": person or _person(pid),
        "professionalSummaries": professionalSummaries or [],
        "experiences": experiences or [],
        "organizations": organizations or [],
        "skills": skills or [],
        "achievements": achievements or [],
        "evidence": evidence or [],
        "education": education or [],
        "certifications": certifications or [],
        "artifacts": artifacts or [],
        "targetContexts": targetContexts or [],
        "projects": projects or [],
        "extensions": {},
    }
    if source_hash or source_name or imported_at:
        acq = {}
        if source_hash:
            acq["sourceHash"] = source_hash
        if source_name:
            acq["sourceName"] = source_name
        if imported_at:
            acq["importedAt"] = imported_at
        data["extensions"]["_acquisition"] = acq
    return data


def _experience(eid: str, title: str, org_id: str | None = None) -> dict:
    exp = {"id": eid, "title": title}
    if org_id:
        exp["organizationRefs"] = [{"id": org_id, "type": "organization"}]
    return exp


def _organization(oid: str, name: str) -> dict:
    return {"id": oid, "name": name}


def _skill(sid: str, name: str, category: str | None = None) -> dict:
    skill = {"id": sid, "name": name}
    if category:
        skill["category"] = category
    return skill


def _education(eid: str, institution: str, program: str) -> dict:
    return {"id": eid, "institutionRef": {"id": institution, "type": "organization"}, "program": program}


def _certification(cid: str, name: str, issuer: str | None = None) -> dict:
    cert = {"id": cid, "name": name}
    if issuer:
        cert["issuerRef"] = {"id": issuer, "type": "organization"}
    return cert


def _project(pid: str, name: str) -> dict:
    return {"id": pid, "name": name}


def _achievement(aid: str, statement: str) -> dict:
    return {"id": aid, "statement": statement}


def _evidence(eid: str, title: str) -> dict:
    return {"id": eid, "title": title}


def _artifact(aid: str, title: str, artifact_type: str = "CV") -> dict:
    return {"id": aid, "title": title, "artifactType": artifact_type}


def _target_context(tid: str, label: str) -> dict:
    return {"id": tid, "label": label}


class TestEntityComparison:
    def test_same_entities_are_same(self) -> None:
        left = [_experience("exp-1", "Engineer", "org-1")]
        right = [_experience("exp-1", "Engineer", "org-1")]
        diffs = _compare_entities(left, right, "experiences")
        assert len(diffs) == 1
        assert diffs[0].diff_type == EntityDiffType.SAME
        assert diffs[0].entity_id == "exp-1"

    def test_different_content_same_id_is_conflict(self) -> None:
        left = [_experience("exp-1", "Engineer", "org-1")]
        right = [_experience("exp-1", "Senior Engineer", "org-1")]
        diffs = _compare_entities(left, right, "experiences")
        assert len(diffs) == 1
        assert diffs[0].diff_type == EntityDiffType.CONFLICT
        assert diffs[0].entity_id == "exp-1"
        assert "different content" in diffs[0].details

    def test_only_in_left(self) -> None:
        left = [_experience("exp-1", "Engineer", "org-1")]
        right = []
        diffs = _compare_entities(left, right, "experiences")
        assert len(diffs) == 1
        assert diffs[0].diff_type == EntityDiffType.ONLY_IN_LEFT
        assert diffs[0].entity_id == "exp-1"

    def test_only_in_right(self) -> None:
        left = []
        right = [_experience("exp-1", "Engineer", "org-1")]
        diffs = _compare_entities(left, right, "experiences")
        assert len(diffs) == 1
        assert diffs[0].diff_type == EntityDiffType.ONLY_IN_RIGHT
        assert diffs[0].entity_id == "exp-1"

    def test_multiple_entities_mixed(self) -> None:
        left = [
            _experience("exp-1", "Engineer", "org-1"),
            _experience("exp-2", "Senior Engineer", "org-1"),
            _experience("exp-3", "Lead", "org-2"),
        ]
        right = [
            _experience("exp-1", "Engineer", "org-1"),
            _experience("exp-2", "Staff Engineer", "org-1"),
            _experience("exp-4", "Principal", "org-3"),
        ]
        diffs = _compare_entities(left, right, "experiences")
        ids = {d.entity_id: d.diff_type for d in diffs}
        assert ids["exp-1"] == EntityDiffType.SAME
        assert ids["exp-2"] == EntityDiffType.CONFLICT
        assert ids["exp-3"] == EntityDiffType.ONLY_IN_LEFT
        assert ids["exp-4"] == EntityDiffType.ONLY_IN_RIGHT


class TestProvenanceWarnings:
    def test_missing_source_hash_warning(self) -> None:
        left = _record("left-profile", _profile("person-1", source_hash=None))
        right = _record("right-profile", _profile("person-2", source_hash="abc123"))
        warnings = _extract_provenance_warnings(left, right)
        types = {w.warning_type for w in warnings}
        assert ProvenanceWarningType.MISSING_SOURCE_HASH in types
        assert any(w.profile_id == "left-profile" for w in warnings)

    def test_missing_source_name_warning(self) -> None:
        left = _record("left-profile", _profile("person-1", source_name=None))
        right = _record("right-profile", _profile("person-2", source_name="cv.docx"))
        warnings = _extract_provenance_warnings(left, right)
        types = {w.warning_type for w in warnings}
        assert ProvenanceWarningType.MISSING_SOURCE_NAME in types

    def test_missing_imported_at_warning(self) -> None:
        left = _record("left-profile", _profile("person-1", imported_at=None))
        right = _record("right-profile", _profile("person-2", imported_at="2026-01-01T00:00:00Z"))
        warnings = _extract_provenance_warnings(left, right)
        types = {w.warning_type for w in warnings}
        assert ProvenanceWarningType.MISSING_IMPORTED_AT in types

    def test_cannot_prove_same_document_when_missing_hash(self) -> None:
        left = _record("left-profile", _profile("person-1", source_hash=None))
        right = _record("right-profile", _profile("person-2", source_hash=None))
        warnings = _extract_provenance_warnings(left, right)
        types = {w.warning_type for w in warnings}
        assert ProvenanceWarningType.CANNOT_PROVE_SAME_DOCUMENT in types
        assert any(w.profile_id == "both" for w in warnings)

    def test_no_warning_when_both_have_hash(self) -> None:
        left = _record("left-profile", _profile("person-1", source_hash="abc123"))
        right = _record("right-profile", _profile("person-2", source_hash="def456"))
        warnings = _extract_provenance_warnings(left, right)
        types = {w.warning_type for w in warnings}
        assert ProvenanceWarningType.MISSING_SOURCE_HASH not in types
        assert ProvenanceWarningType.CANNOT_PROVE_SAME_DOCUMENT not in types


class TestReconciliation:
    def test_same_human_different_ids(self) -> None:
        """Phase 3A: canonical vs staging with different deterministic IDs but same human."""
        left = _record(
            "raul-gongora-profile",
            _profile(
                "person-raul-gongora",
                person=_person("person-raul-gongora", name="Raul Gongora Betancourt", email="raul@example.com", phone="+46 70 123 45 67"),
            ),
        )
        right = _record(
            "person-raul-gongora-betancourt-profile",
            _profile(
                "person-raul-gongora-betancourt",
                person=_person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt", email="raul@example.com", phone="+46701234567"),
            ),
        )
        plan = reconcile_profiles(left, right)
        
        matched, conflicting = plan.identity_comparison
        assert "email" in matched
        assert "phone" in matched
        assert not conflicting
        assert plan.left_person_id == "person-raul-gongora"
        assert plan.right_person_id == "person-raul-gongora-betancourt"

    def test_canonical_vs_staging(self) -> None:
        """Canonical profile vs staging profile reconciliation."""
        left = _record(
            "raul-gongora-profile",
            _profile(
                "person-raul-gongora",
                person=_person("person-raul-gongora", name="Raul Gongora Betancourt", email="raul@example.com"),
                experiences=[
                    _experience("exp-1", "Engineer", "org-1"),
                    _experience("exp-2", "Senior Engineer", "org-2"),
                ],
                organizations=[
                    _organization("org-1", "Google Cloud"),
                    _organization("org-2", "Acme Corp"),
                ],
                skills=[_skill("skill-1", "Python"), _skill("skill-2", "Cloud")],
            ),
        )
        right = _record(
            "person-raul-gongora-betancourt-profile",
            _profile(
                "person-raul-gongora-betancourt",
                person=_person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt", email="raul@example.com"),
                experiences=[
                    _experience("exp-1", "Engineer", "org-1"),
                    _experience("exp-3", "Lead Engineer", "org-3"),
                ],
                organizations=[
                    _organization("org-1", "Google Cloud"),
                    _organization("org-3", "Startup Inc"),
                ],
                skills=[_skill("skill-1", "Python")],
            ),
        )
        plan = reconcile_profiles(left, right)
        
        diff_types = {d.diff_type for d in plan.entity_diffs}
        assert EntityDiffType.SAME in diff_types  # exp-1, org-1, skill-1
        assert EntityDiffType.ONLY_IN_LEFT in diff_types  # exp-2, org-2, skill-2
        assert EntityDiffType.ONLY_IN_RIGHT in diff_types  # exp-3, org-3
        # No conflicts since entities have different IDs

    def test_staging_vs_staging(self) -> None:
        """Two staging profiles for the same human."""
        left = _record(
            "person-gongora-profile",
            _profile(
                "person-gongora",
                person=_person("person-gongora", name="Raul Gongora Betancourt", email="old@example.com"),
            ),
        )
        right = _record(
            "person-raul-gongora-betancourt-profile",
            _profile(
                "person-raul-gongora-betancourt",
                person=_person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt", email="new@example.com"),
            ),
        )
        plan = reconcile_profiles(left, right)
        
        matched, conflicting = plan.identity_comparison
        assert "name" in matched
        assert "email" in conflicting

    def test_matching_entities(self) -> None:
        """Entities with identical content are marked SAME."""
        left = _record("left", _profile("p1", person=_person("p1"), skills=[_skill("s1", "Python")]))
        right = _record("right", _profile("p2", person=_person("p2"), skills=[_skill("s1", "Python")]))
        plan = reconcile_profiles(left, right)
        skills_diffs = [d for d in plan.entity_diffs if d.entity_type == "skills"]
        assert len(skills_diffs) == 1
        assert skills_diffs[0].diff_type == EntityDiffType.SAME

    def test_conflicting_entities(self) -> None:
        """Entities with same ID but different content are CONFLICT."""
        left = _record("left", _profile("p1", person=_person("p1"), skills=[_skill("s1", "Python")]))
        right = _record("right", _profile("p2", person=_person("p2"), skills=[_skill("s1", "Python Advanced")]))
        plan = reconcile_profiles(left, right)
        skills_diffs = [d for d in plan.entity_diffs if d.entity_type == "skills"]
        assert len(skills_diffs) == 1
        assert skills_diffs[0].diff_type == EntityDiffType.CONFLICT

    def test_left_unique_entities(self) -> None:
        """Entities only in left profile are ONLY_IN_LEFT."""
        left = _record("left", _profile("p1", person=_person("p1"), skills=[_skill("s1", "Python"), _skill("s2", "Java")]))
        right = _record("right", _profile("p2", person=_person("p2"), skills=[_skill("s1", "Python")]))
        plan = reconcile_profiles(left, right)
        skills_diffs = {d.entity_id: d.diff_type for d in plan.entity_diffs if d.entity_type == "skills"}
        assert skills_diffs["s1"] == EntityDiffType.SAME
        assert skills_diffs["s2"] == EntityDiffType.ONLY_IN_LEFT

    def test_right_unique_entities(self) -> None:
        """Entities only in right profile are ONLY_IN_RIGHT."""
        left = _record("left", _profile("p1", person=_person("p1"), skills=[_skill("s1", "Python")]))
        right = _record("right", _profile("p2", person=_person("p2"), skills=[_skill("s1", "Python"), _skill("s2", "Java")]))
        plan = reconcile_profiles(left, right)
        skills_diffs = {d.entity_id: d.diff_type for d in plan.entity_diffs if d.entity_type == "skills"}
        assert skills_diffs["s1"] == EntityDiffType.SAME
        assert skills_diffs["s2"] == EntityDiffType.ONLY_IN_RIGHT

    def test_missing_provenance_warnings(self) -> None:
        """Profiles without sourceHash/sourceName/importedAt emit warnings."""
        left = _record("left", _profile("p1", person=_person("p1")))  # no provenance
        right = _record("right", _profile("p2", person=_person("p2"), source_hash="abc123", source_name="cv.docx", imported_at="2026-01-01T00:00:00Z"))
        plan = reconcile_profiles(left, right)
        
        warning_types = {w.warning_type for w in plan.provenance_warnings}
        assert ProvenanceWarningType.MISSING_SOURCE_HASH in warning_types
        assert ProvenanceWarningType.MISSING_SOURCE_NAME in warning_types
        assert ProvenanceWarningType.MISSING_IMPORTED_AT in warning_types
        assert ProvenanceWarningType.CANNOT_PROVE_SAME_DOCUMENT in warning_types

    def test_deterministic_output(self) -> None:
        """Repeated reconciliation produces identical results."""
        left = _record("left", _profile("p1", person=_person("p1", name="Raul Gongora Betancourt", email="raul@example.com")))
        right = _record("right", _profile("p2", person=_person("p2", name="Raul Gongora Betancourt", email="raul@example.com")))
        
        plan1 = reconcile_profiles(left, right)
        plan2 = reconcile_profiles(left, right)
        
        assert plan1.identity_comparison == plan2.identity_comparison
        assert len(plan1.entity_diffs) == len(plan2.entity_diffs)
        for d1, d2 in zip(plan1.entity_diffs, plan2.entity_diffs):
            assert d1.entity_type == d2.entity_type
            assert d1.entity_id == d2.entity_id
            assert d1.diff_type == d2.diff_type
        
        plan1 = reconcile_profiles(left, right)
        plan2 = reconcile_profiles(left, right)
        
        assert plan1.identity_comparison == plan2.identity_comparison
        assert len(plan1.entity_diffs) == len(plan2.entity_diffs)
        for d1, d2 in zip(plan1.entity_diffs, plan2.entity_diffs):
            assert d1.entity_type == d2.entity_type
            assert d1.entity_id == d2.entity_id
            assert d1.diff_type == d2.diff_type

    def test_unknown_profile_handling(self) -> None:
        """Reconciliation with None records should not crash."""
        left = _record("left", _profile("p1", person=_person("p1", name="Raul", email="raul@example.com")))
        plan = reconcile_profiles(left, None)
        
        assert plan.right_profile_id == "unknown"
        assert plan.right_person_id is None
        assert plan.identity_comparison == ((), ())
        
        plan2 = reconcile_profiles(None, left)
        assert plan2.left_profile_id == "unknown"

    def test_different_entities_all_types(self) -> None:
        """All entity types are compared."""
        left = _record("left", _profile("p1", person=_person("p1"),
            experiences=[_experience("e1", "Eng")],
            organizations=[_organization("o1", "Org")],
            skills=[_skill("s1", "Skill")],
            education=[_education("edu1", "inst1", "Program")],
            certifications=[_certification("c1", "Cert")],
            projects=[_project("p1", "Project")],
            achievements=[_achievement("a1", "Achievement")],
            evidence=[_evidence("ev1", "Evidence")],
            artifacts=[_artifact("art1", "Artifact")],
            targetContexts=[_target_context("tc1", "Context")],
        ))
        right = _record("right", _profile("p2", person=_person("p2")))
        
        plan = reconcile_profiles(left, right)
        
        entity_types = {d.entity_type for d in plan.entity_diffs}
        expected_types = {
            "experiences", "organizations", "skills", "education",
            "certifications", "projects", "achievements", "evidence",
            "artifacts", "targetContexts"
        }
        assert expected_types.issubset(entity_types)

    def test_professional_summaries_compared(self) -> None:
        left = _record("left", _profile("p1", person=_person("p1"), professionalSummaries=[{"id": "s1", "text": "Summary"}]))
        right = _record("right", _profile("p2", person=_person("p2"), professionalSummaries=[{"id": "s1", "text": "Different"}]))
        plan = reconcile_profiles(left, right)
        summaries = [d for d in plan.entity_diffs if d.entity_type == "professionalSummaries"]
        assert len(summaries) == 1
        assert summaries[0].diff_type == EntityDiffType.CONFLICT


class TestReconciliationOutputFormat:
    def test_format_yaml_output(self) -> None:
        from careeros.reconciliation import format_reconciliation_plan
        
        left = _record("left", _profile("p1", person=_person("p1", name="Raul")))
        right = _record("right", _profile("p2", person=_person("p2", name="Raul")))
        plan = reconcile_profiles(left, right)
        
        yaml_output = format_reconciliation_plan(plan, output_format="yaml")
        assert "leftProfileId" in yaml_output
        assert "rightProfileId" in yaml_output
        assert "entityDiffs" in yaml_output

    def test_format_json_output(self) -> None:
        from careeros.reconciliation import format_reconciliation_plan
        
        left = _record("left", _profile("p1", person=_person("p1", name="Raul")))
        right = _record("right", _profile("p2", person=_person("p2", name="Raul")))
        plan = reconcile_profiles(left, right)
        
        json_output = format_reconciliation_plan(plan, output_format="json")
        assert '"leftProfileId"' in json_output
        assert '"rightProfileId"' in json_output


class TestLoadProfiles:
    def test_load_profiles_from_temp_dir(self, tmp_path: Path) -> None:
        from careeros.reconciliation import load_profiles_for_reconciliation
        
        # Create two profiles in temp dir
        left_data = _profile("person-left", person=_person("person-left", name="Left Person"))
        right_data = _profile("person-right", person=_person("person-right", name="Right Person"))
        
        staging = tmp_path / "staging"
        staging.mkdir()
        
        left_path = staging / "person-left-profile.yaml"
        right_path = staging / "person-right-profile.yaml"
        
        import yaml
        left_path.write_text(yaml.safe_dump(left_data), encoding="utf-8")
        right_path.write_text(yaml.safe_dump(right_data), encoding="utf-8")
        
        left_record, right_record = load_profiles_for_reconciliation(tmp_path, "person-left-profile", "person-right-profile")
        
        assert left_record is not None
        assert right_record is not None
        assert left_record.profile_id == "person-left-profile"
        assert right_record.profile_id == "person-right-profile"

    def test_load_missing_profile_returns_none(self, tmp_path: Path) -> None:
        from careeros.reconciliation import load_profiles_for_reconciliation
        
        left_record, right_record = load_profiles_for_reconciliation(tmp_path, "nonexistent", "also-missing")
        
        assert left_record is None
        assert right_record is None