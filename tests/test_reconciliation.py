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


# ---------------------------------------------------------------------------
# Phase 3B: deterministic cross-ID evidence matching
# ---------------------------------------------------------------------------

def _real_experience(
    eid: str,
    title: str,
    org_id: str,
    start: str,
    end: str | None,
    scope: str | None = None,
) -> dict:
    exp: dict = {
        "id": eid,
        "title": title,
        "organizationRefs": [{"id": org_id, "type": "organization"}],
        "dateRange": {"start": start, "end": end, "isCurrent": False},
        "engagementType": "Full-time",
    }
    if scope:
        exp["scope"] = scope
    return exp


def _real_organization(oid: str, name: str) -> dict:
    return {"id": oid, "name": name}


def _real_skill(sid: str, name: str, category: str) -> dict:
    return {"id": sid, "name": name, "category": category}


class TestEvidenceMatching:
    """Phase 3B: cross-ID evidence matching on observed real-world cases."""

    def test_experience_cross_id_match_title_and_dates(self) -> None:
        """exp-qred-bank2 ↔ exp-gongora-betancourt-senior-devsecops-specialist
        share title + dateRange despite different IDs."""
        from careeros.evidence import match_entities

        left = [_real_experience(
            "exp-qred-bank2", "Senior DevSecOps Specialist", "org-vmware-vxrail-datacenters-to-aws",
            "2023-05", "2024-12",
        )]
        right = [_real_experience(
            "exp-gongora-betancourt-senior-devsecops-specialist", "Senior DevSecOps Specialist",
            "org-selfemployed", "2023-05", "2024-12",
            scope="Led migration from VMware VxRail datacenters to AWS, reducing infrastructure overhead by over 50%",
        )]
        matches = match_entities("experiences", left, right)
        assert len(matches) == 1
        assert matches[0].left_entity_id == "exp-qred-bank2"
        assert matches[0].right_entity_id == "exp-gongora-betancourt-senior-devsecops-specialist"
        assert matches[0].matched_on == ("title", "dateRange")

    def test_experience_cross_id_match_title_tokens_and_dates(self) -> None:
        """exp-qred-bank5 ↔ exp-acmecorp5 match on title-token containment + exact dates."""
        from careeros.evidence import match_entities

        left = [_real_experience(
            "exp-qred-bank5", "System Administrator / IT Engineer", "org-distributed-hotel-systems-integration",
            "1996-08", "2001-04",
        )]
        right = [_real_experience(
            "exp-acmecorp5", "System Administrator", "org-acme-corp",
            "1996-08", "2001-04",
            scope="Spearheaded integration of distributed hotel systems into a standardized, secure central IT structure.",
        )]
        matches = match_entities("experiences", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("title-tokens", "dateRange")

    def test_different_roles_do_not_match(self) -> None:
        """exp-qred-bank2 (Senior DevSecOps Specialist) and exp-acmecorp2
        (System Developer & AI Architect) are distinct roles and must not match."""
        from careeros.evidence import match_entities

        left = [_real_experience(
            "exp-qred-bank2", "Senior DevSecOps Specialist", "org-vmware-vxrail-datacenters-to-aws",
            "2023-05", "2024-12",
        )]
        right = [_real_experience(
            "exp-acmecorp2", "System Developer & AI Architect", "org-acme-corp",
            "2022-02", "2023-04",
            scope="Architected, coded, and deployed accent-mvp; built Python Django REST APIs and React frontend.",
        )]
        matches = match_entities("experiences", left, right)
        assert matches == []

    def test_skill_token_containment(self) -> None:
        """skill-agentic-ai-&-engineering ↔ skill-agentic-ai share the Agentic AI skill."""
        from careeros.evidence import match_entities

        left = [_real_skill("skill-agentic-ai-&-engineering", "Agentic AI & Engineering", "AI and Machine Learning")]
        right = [_real_skill("skill-agentic-ai", "Agentic AI", "AI & Machine Learning")]
        matches = match_entities("skills", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("name-tokens",)

    def test_skill_exact_name_match(self) -> None:
        from careeros.evidence import match_entities

        left = [_real_skill("skill-cloud-&-containers", "Cloud & Containers", "Cloud")]
        right = [_real_skill("skill-cloud", "Cloud", "Cloud Platform")]
        matches = match_entities("skills", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("name-tokens",)

    def test_skill_no_containment_no_match(self) -> None:
        from careeros.evidence import match_entities

        left = [_real_skill("skill-network-&-monitoring", "Network & Monitoring", "Networking")]
        right = [_real_skill("skill-networking", "Networking", "Network & Monitoring")]
        matches = match_entities("skills", left, right)
        assert matches == []

    def test_organization_name_variants(self) -> None:
        """Organization names that normalize the same (case/punctuation) match."""
        from careeros.evidence import match_entities

        left = [_real_organization("org-left", "ACME Corp")]
        right = [_real_organization("org-right", "Acme Corp.")]
        matches = match_entities("organizations", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("name",)

    def test_organization_company_abbreviation(self) -> None:
        from careeros.evidence import match_entities

        left = [_real_organization("org-ibm", "International Business Machines")]
        right = [_real_organization("org-ibm2", "IBM")]
        matches = match_entities("organizations", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("name",)

    def test_organization_different_names_no_match(self) -> None:
        from careeros.evidence import match_entities

        left = [_real_organization("org-google-cloud", "Google Cloud")]
        right = [_real_organization("org-acme-corp", "ACME Corp")]
        matches = match_entities("organizations", left, right)
        assert matches == []

    def test_education_program_match(self) -> None:
        from careeros.evidence import match_entities

        left = [{
            "id": "edu-left",
            "institutionRef": {"id": "org-kth", "type": "organization"},
            "program": "Master's Degree",
        }]
        right = [{
            "id": "edu-right",
            "institutionRef": {"id": "org-kth-2", "type": "organization"},
            "program": "Master's Degree",
        }]
        matches = match_entities("education", left, right)
        assert len(matches) == 1
        assert matches[0].matched_on == ("program",)

    def test_education_institution_and_dates_match(self) -> None:
        from careeros.evidence import match_entities

        left = [{
            "id": "edu-left",
            "institutionRef": {"id": "org-kth", "type": "organization"},
            "program": "M.S.",
            "dateRange": {"start": "1985-08", "end": "1990-06", "isCurrent": False},
        }]
        right = [{
            "id": "edu-right",
            "institutionRef": {"id": "org-kth-2", "type": "organization"},
            "program": "M.S.",
            "dateRange": {"start": "1985-09", "end": "1990-06", "isCurrent": False},
        }]
        org_names = {"org-kth": "KTH Royal Institute of Technology", "org-kth-2": "KTH Royal Institute of Technology"}
        matches = match_entities("education", left, right, org_names, org_names)
        assert len(matches) == 1
        assert "program" in matches[0].matched_on
        assert "dateRange-overlap" in matches[0].matched_on

    def test_one_to_one_matching(self) -> None:
        """Each right entity can be consumed at most once."""
        from careeros.evidence import match_entities

        left = [
            _real_experience("exp-a1", "Senior DevSecOps Specialist", "org-x", "2023-05", "2024-12"),
            _real_experience("exp-b1", "Founder & CEO", "org-x", "2019-08", "2022-01"),
        ]
        right = [
            _real_experience("exp-a2", "Senior DevSecOps Specialist", "org-y", "2023-05", "2024-12"),
            _real_experience("exp-b2", "Founder & CEO", "org-y", "2019-08", "2022-01"),
        ]
        matches = match_entities("experiences", left, right)
        assert len(matches) == 2
        right_ids = {m.right_entity_id for m in matches}
        assert right_ids == {"exp-a2", "exp-b2"}

    def test_deterministic_matching(self) -> None:
        from careeros.evidence import match_entities

        left = [
            _real_experience("exp-qred-bank", "Senior IT System Administrator & DevSecOps Specialist", "org-google-cloud", "2025-03", "2025-12"),
            _real_experience("exp-qred-bank2", "Senior DevSecOps Specialist", "org-vmware-vxrail-datacenters-to-aws", "2023-05", "2024-12"),
            _real_experience("exp-qred-bank3", "Founder & CEO", "org-healthcaresector-business", "2019-08", "2022-01"),
        ]
        right = [
            _real_experience("exp-acmecorp3", "Founder & CEO", "org-acme-corp", "2019-08", "2022-01"),
            _real_experience("exp-gongora-betancourt-senior-devsecops-specialist", "Senior DevSecOps Specialist", "org-selfemployed", "2023-05", "2024-12"),
            _real_experience("exp-gongora-betancourt-senior-system-administrator", "Senior IT System Administrator & DevSecOps Specialist", "org-selfemployed", "2025-03", "2025-12"),
        ]
        matches1 = match_entities("experiences", left, right)
        matches2 = match_entities("experiences", left, right)
        assert [(m.left_entity_id, m.right_entity_id, m.matched_on) for m in matches1] == \
               [(m.left_entity_id, m.right_entity_id, m.matched_on) for m in matches2]


class TestReconciliationWithEvidence:
    """Phase 3B: reconciliation reclassifies cross-ID evidence matches."""

    def test_real_world_staging_pair_reclassified(self) -> None:
        """The observed exp-qred-bank* family now matches its betancourt counterparts."""
        left = _record(
            "person-gongora-profile",
            _profile(
                "person-gongora",
                person=_person("person-gongora", name="Raul Gongora Betancourt"),
                experiences=[
                    _real_experience("exp-qred-bank", "Senior IT System Administrator & DevSecOps Specialist", "org-google-cloud", "2025-03", "2025-12"),
                    _real_experience("exp-qred-bank2", "Senior DevSecOps Specialist", "org-vmware-vxrail-datacenters-to-aws", "2023-05", "2024-12"),
                    _real_experience("exp-qred-bank3", "Founder & CEO", "org-healthcaresector-business", "2019-08", "2022-01"),
                    _real_experience("exp-qred-bank4", "System Administrator / IT Engineer", "org-largescale-windows-and-linux-environments", "2001-05", "2019-08"),
                    _real_experience("exp-qred-bank5", "System Administrator / IT Engineer", "org-distributed-hotel-systems-integration", "1996-08", "2001-04"),
                ],
                organizations=[
                    _real_organization("org-google-cloud", "Google Cloud"),
                    _real_organization("org-vmware-vxrail-datacenters-to-aws", "VMware VxRail datacenters to AWS"),
                    _real_organization("org-healthcaresector-business", "Healthcare-sector business"),
                    _real_organization("org-largescale-windows-and-linux-environments", "Large-scale Windows and Linux environments"),
                    _real_organization("org-distributed-hotel-systems-integration", "Distributed hotel systems integration"),
                ],
                skills=[
                    _real_skill("skill-agentic-ai-&-engineering", "Agentic AI & Engineering", "AI and Machine Learning"),
                    _real_skill("skill-cloud-&-containers", "Cloud & Containers", "Cloud Computing and Containerization"),
                    _real_skill("skill-infrastructure-&-os", "Infrastructure & OS", "IT Infrastructure and Operating Systems"),
                    _real_skill("skill-network-&-monitoring", "Network & Monitoring", "Networking and Monitoring"),
                    _real_skill("skill-web-&-databases", "Web & Databases", "Web Development and Databases"),
                ],
            ),
        )
        right = _record(
            "person-raul-gongora-betancourt-profile",
            _profile(
                "person-raul-gongora-betancourt",
                person=_person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt"),
                experiences=[
                    _real_experience("exp-gongora-betancourt-senior-system-administrator", "Senior IT System Administrator & DevSecOps Specialist", "org-selfemployed", "2025-03", "2025-12"),
                    _real_experience("exp-gongora-betancourt-senior-devsecops-specialist", "Senior DevSecOps Specialist", "org-selfemployed", "2023-05", "2024-12"),
                    _real_experience("exp-acmecorp3", "Founder & CEO", "org-acme-corp", "2019-08", "2022-01"),
                    _real_experience("exp-acmecorp4", "System Administrator / IT Engineer", "org-acme-corp", "2001-05", "2019-08"),
                    _real_experience("exp-acmecorp5", "System Administrator", "org-acme-corp", "1996-08", "2001-04"),
                    _real_experience("exp-acmecorp", "Senior Engineer", "org-acme-corp", "2023-05", None),
                    _real_experience("exp-acmecorp2", "System Developer & AI Architect", "org-acme-corp", "2022-02", "2023-04"),
                ],
                organizations=[
                    _real_organization("org-selfemployed", "Self-employed"),
                    _real_organization("org-acme-corp", "ACME Corp"),
                ],
                skills=[
                    _real_skill("skill-agentic-ai", "Agentic AI", "AI & Machine Learning"),
                    _real_skill("skill-cloud", "Cloud", "Cloud Platform"),
                    _real_skill("skill-infrastructure", "Infrastructure", "Infrastructure & OS"),
                    _real_skill("skill-web", "Web", "Web & Databases"),
                    _real_skill("skill-python", "Python", "Programming Language"),
                ],
            ),
        )
        plan = reconcile_profiles(left, right)

        experience_diffs = {d.entity_id: d for d in plan.entity_diffs if d.entity_type == "experiences"}
        assert experience_diffs["exp-qred-bank"].diff_type == EntityDiffType.CONFLICT
        assert experience_diffs["exp-qred-bank"].matched_on == ("title", "dateRange")
        assert experience_diffs["exp-qred-bank"].matched_with == "exp-gongora-betancourt-senior-system-administrator"
        assert experience_diffs["exp-qred-bank2"].matched_with == "exp-gongora-betancourt-senior-devsecops-specialist"
        assert experience_diffs["exp-qred-bank3"].matched_with == "exp-acmecorp3"
        assert experience_diffs["exp-qred-bank4"].matched_with == "exp-acmecorp4"
        assert experience_diffs["exp-qred-bank5"].matched_on == ("title-tokens", "dateRange")
        assert experience_diffs["exp-qred-bank5"].matched_with == "exp-acmecorp5"
        # exp-acmecorp and exp-acmecorp2 have no cross-ID counterpart in the left profile
        assert experience_diffs["exp-acmecorp"].diff_type == EntityDiffType.ONLY_IN_RIGHT
        assert experience_diffs["exp-acmecorp2"].diff_type == EntityDiffType.ONLY_IN_RIGHT

        skill_diffs = {d.entity_id: d for d in plan.entity_diffs if d.entity_type == "skills"}
        assert skill_diffs["skill-agentic-ai-&-engineering"].matched_with == "skill-agentic-ai"
        assert skill_diffs["skill-agentic-ai-&-engineering"].matched_on == ("name-tokens",)
        assert skill_diffs["skill-cloud-&-containers"].matched_with == "skill-cloud"
        assert skill_diffs["skill-network-&-monitoring"].diff_type == EntityDiffType.ONLY_IN_LEFT
        assert skill_diffs["skill-python"].diff_type == EntityDiffType.ONLY_IN_RIGHT

    def test_evidence_same_when_content_equal(self) -> None:
        """Cross-ID matches with identical content are reclassified as SAME."""
        left = _record(
            "left",
            _profile(
                "p1",
                person=_person("p1", name="Raul"),
                skills=[_real_skill("skill-a-&-b", "Agentic AI", "AI")],
            ),
        )
        right = _record(
            "right",
            _profile(
                "p2",
                person=_person("p2", name="Raul"),
                skills=[_real_skill("skill-a", "Agentic AI", "AI")],
            ),
        )
        plan = reconcile_profiles(left, right)
        skill_diffs = {d.entity_id: d for d in plan.entity_diffs if d.entity_type == "skills"}
        assert skill_diffs["skill-a-&-b"].diff_type == EntityDiffType.SAME
        assert skill_diffs["skill-a-&-b"].matched_on == ("name",)
        assert skill_diffs["skill-a-&-b"].matched_with == "skill-a"

    def test_by_id_semantics_preserved_for_artifacts(self) -> None:
        """Artifacts keep by-ID semantics (no cross-ID evidence matching)."""
        left = _record(
            "left",
            _profile(
                "p1",
                person=_person("p1", name="Raul"),
                artifacts=[{"id": "artf-cv-left", "title": "Tailored CV", "artifactType": "CV"}],
            ),
        )
        right = _record(
            "right",
            _profile(
                "p2",
                person=_person("p2", name="Raul"),
                artifacts=[{"id": "artf-cv-right", "title": "Tailored CV", "artifactType": "CV"}],
            ),
        )
        plan = reconcile_profiles(left, right)
        artifact_diffs = {d.entity_id: d for d in plan.entity_diffs if d.entity_type == "artifacts"}
        assert artifact_diffs["artf-cv-left"].diff_type == EntityDiffType.ONLY_IN_LEFT
        assert artifact_diffs["artf-cv-left"].matched_on == ()
        assert artifact_diffs["artf-cv-right"].diff_type == EntityDiffType.ONLY_IN_RIGHT

    def test_by_id_semantics_preserved_for_professional_summaries(self) -> None:
        left = _record(
            "left",
            _profile(
                "p1",
                person=_person("p1", name="Raul"),
                professionalSummaries=[{"id": "summary-1", "text": "Summary text"}],
            ),
        )
        right = _record(
            "right",
            _profile(
                "p2",
                person=_person("p2", name="Raul"),
                professionalSummaries=[{"id": "summary-2", "text": "Summary text"}],
            ),
        )
        plan = reconcile_profiles(left, right)
        summary_diffs = {d.entity_id: d for d in plan.entity_diffs if d.entity_type == "professionalSummaries"}
        assert summary_diffs["summary-1"].diff_type == EntityDiffType.ONLY_IN_LEFT
        assert summary_diffs["summary-2"].diff_type == EntityDiffType.ONLY_IN_RIGHT

    def test_format_includes_evidence_fields(self) -> None:
        from careeros.reconciliation import format_reconciliation_plan

        left = _record(
            "left",
            _profile(
                "p1",
                person=_person("p1", name="Raul"),
                skills=[_real_skill("skill-a-&-b", "Agentic AI & Engineering", "AI")],
            ),
        )
        right = _record(
            "right",
            _profile(
                "p2",
                person=_person("p2", name="Raul"),
                skills=[_real_skill("skill-a", "Agentic AI", "AI")],
            ),
        )
        plan = reconcile_profiles(left, right)
        yaml_output = format_reconciliation_plan(plan, output_format="yaml")
        assert "matchedOn" in yaml_output
        assert "name-tokens" in yaml_output
        json_output = format_reconciliation_plan(plan, output_format="json")
        assert '"matchedOn"' in json_output
        assert '"matchedWith": "skill-a"' in json_output
