from __future__ import annotations

from typing import Any

import pytest

from careeros.knowledge import KnowledgeGraphBuilder
from careeros.reasoning import ReasoningEngine, ReasoningResult, RuleContext
from careeros.reasoning.rules import (
    CareerHighlightsRule,
    CloudExperienceRule,
    DomainExperienceRule,
    LeadershipExperienceRule,
    SeniorResponsibilityRule,
    StrongestExperienceRule,
    TechnologyBreadthRule,
)
from careeros.reasoning.utils import (
    detect_cloud_provider,
    detect_industry,
    detect_leadership_role,
    detect_responsibility_areas,
    has_migration_keywords,
    word_boundary_match,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    person_id: str = "person-test",
    experiences: list[dict[str, Any]] | None = None,
    skills: list[dict[str, Any]] | None = None,
    organizations: list[dict[str, Any]] | None = None,
) -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": person_id,
            "names": [{"value": "Test User", "usage": "professional"}],
        },
        "experiences": experiences or [],
        "skills": skills or [],
        "education": [],
        "organizations": (
            organizations
            if organizations is not None
            else _collect_orgs(experiences)
        ),
        "professionalSummaries": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
    }


def _collect_orgs(experiences: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    seen: set[str] = set()
    orgs: list[dict[str, Any]] = []
    for exp in experiences or []:
        for ref in exp.get("organizationRefs", []):
            oid = ref.get("id")
            if oid and oid not in seen:
                seen.add(oid)
                orgs.append({"id": oid, "name": ref.get("name", oid)})
    return orgs


def _exp(
    eid: str,
    title: str,
    org_name: str,
    org_id: str,
    start: str | None = None,
    end: str | None = None,
    is_current: bool = False,
    scope: str | None = None,
) -> dict:
    dr: dict[str, Any] = {}
    if start is not None:
        dr["start"] = start
    if end is not None:
        dr["end"] = end
    if is_current:
        dr["isCurrent"] = True
    result: dict[str, Any] = {
        "id": eid,
        "title": title,
        "organizationRefs": [
            {"id": org_id, "name": org_name, "type": "organization"}
        ],
        "dateRange": dr,
    }
    if scope is not None:
        result["scope"] = scope
    return result


def _skill(
    sid: str,
    name: str,
    category: str = "General",
    experience_ids: list[str] | None = None,
) -> dict:
    evidence = []
    if experience_ids:
        for eid in experience_ids:
            evidence.append({"experienceId": eid})
    skill: dict[str, Any] = {
        "id": sid,
        "name": name,
        "category": category,
    }
    if evidence:
        skill["extensions"] = {"experienceEvidence": evidence}
    return skill


def _run_rule(rule, experiences=None, skills=None, orgs=None, **params) -> list[ReasoningResult]:
    profile = _profile(
        experiences=experiences or [],
        skills=skills or [],
        organizations=orgs,
    )
    graph = KnowledgeGraphBuilder().build(profile)
    context = RuleContext(graph=graph, profile=profile, parameters=params)
    return rule.execute(context)


# ===================================================================
# lookup utility tests
# ===================================================================


def test_word_boundary_match_simple() -> None:
    assert word_boundary_match("aws", "I use AWS for cloud")
    assert word_boundary_match("aws", "aws is great")
    assert not word_boundary_match("aws", "claws")


def test_word_boundary_match_multi_word() -> None:
    assert word_boundary_match("vice president", "Vice President of Engineering")
    assert not word_boundary_match("vice president", "President")


def test_word_boundary_match_case_insensitive() -> None:
    assert word_boundary_match("AWS", "I use aws")


def test_detect_cloud_provider_aws() -> None:
    assert detect_cloud_provider("AWS") == "AWS"
    assert detect_cloud_provider("Amazon S3") == "AWS"
    assert detect_cloud_provider("Lambda") == "AWS"


def test_detect_cloud_provider_azure() -> None:
    assert detect_cloud_provider("Azure Functions") == "Azure"
    assert detect_cloud_provider("Microsoft Azure") == "Azure"


def test_detect_cloud_provider_gcp() -> None:
    assert detect_cloud_provider("Google Cloud Platform") == "GCP"
    assert detect_cloud_provider("BigQuery") == "GCP"


def test_detect_cloud_provider_none() -> None:
    assert detect_cloud_provider("Python") is None
    assert detect_cloud_provider("Django") is None


def test_detect_cloud_provider_substring_no_false_positive() -> None:
    # "aws" should not match inside "claws" or "paws"
    assert detect_cloud_provider("claws") is None


def test_detect_industry_finance() -> None:
    assert detect_industry("Goldman Sachs", "Analyst") is None  # too generic
    assert detect_industry("Bank of America", "Teller") == "Finance"


def test_detect_industry_healthcare() -> None:
    assert detect_industry("Mayo Clinic", "Doctor") is None  # not keyword
    assert detect_industry("Healthcare Corp", "Engineer") == "Healthcare"


def test_detect_industry_tech() -> None:
    assert detect_industry("Acme Software", "Engineer") == "Technology"


def test_detect_industry_none() -> None:
    assert detect_industry("Unknown Company", "Generic Role") is None


def test_detect_leadership_role_manager() -> None:
    assert detect_leadership_role("Engineering Manager") is not None


def test_detect_leadership_role_director() -> None:
    assert detect_leadership_role("Director of Engineering") is not None


def test_detect_leadership_role_architect() -> None:
    assert detect_leadership_role("Solutions Architect") is not None


def test_detect_leadership_role_plain_engineer() -> None:
    assert detect_leadership_role("Software Engineer") is None


def test_detect_leadership_role_cto() -> None:
    assert detect_leadership_role("CTO") is not None


def test_detect_responsibility_areas_architecture() -> None:
    areas = detect_responsibility_areas("Software Architect")
    assert "architecture" in areas


def test_detect_responsibility_areas_devops() -> None:
    areas = detect_responsibility_areas("DevOps Engineer")
    assert "devops" in areas


def test_detect_responsibility_areas_security() -> None:
    areas = detect_responsibility_areas("Security Engineer")
    assert "security" in areas


def test_detect_responsibility_areas_mentoring() -> None:
    areas = detect_responsibility_areas("Team Lead")
    assert "mentoring" in areas


def test_detect_responsibility_areas_multiple() -> None:
    areas = detect_responsibility_areas(
        "DevOps Architect", scope="Cloud migration and security"
    )
    assert "devops" in areas
    assert "migrations" in areas
    assert "security" in areas


def test_detect_responsibility_areas_none() -> None:
    areas = detect_responsibility_areas("Junior Engineer")
    assert areas == {}


def test_has_migration_keywords_true() -> None:
    assert has_migration_keywords("Cloud Migration Lead")
    assert has_migration_keywords("Engineer", scope="Data migration project")


def test_has_migration_keywords_false() -> None:
    assert not has_migration_keywords("Software Engineer")


# ===================================================================
# StrongestExperienceRule
# ===================================================================


def test_strongest_experience_empty() -> None:
    results = _run_rule(StrongestExperienceRule(), [])
    assert len(results) == 1
    assert results[0].value == []


def test_strongest_experience_single() -> None:
    exps = [_exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01")]
    results = _run_rule(StrongestExperienceRule(), exps)
    assert len(results[0].value) == 1
    assert results[0].value[0]["experience_id"] == "e1"
    assert results[0].value[0]["score"] > 0


def test_strongest_experience_ranking() -> None:
    exps = [
        _exp("e1", "Junior Engineer", "Acme", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Senior Engineer", "Beta", "org-2", "2021-01", "2024-01"),
    ]
    results = _run_rule(StrongestExperienceRule(), exps)
    ranked = results[0].value
    assert len(ranked) == 2
    assert ranked[0]["experience_id"] == "e2"  # longer + higher title


def test_strongest_experience_leadership_boost() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Manager", "Beta", "org-2", "2021-01", "2023-01"),
    ]
    results = _run_rule(StrongestExperienceRule(), exps)
    ranked = results[0].value
    # e2 has leadership (Manager) so should rank higher despite shorter duration
    assert ranked[0]["experience_id"] == "e2"


def test_strongest_experience_scope_boost() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Engineer", "Beta", "org-2", "2021-01", "2023-01", scope="Led major project"),
    ]
    results = _run_rule(StrongestExperienceRule(), exps)
    ranked = results[0].value
    assert ranked[0]["experience_id"] == "e2"  # has scope


def test_strongest_experience_deterministic() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2022-01"),
        _exp("e2", "Senior Engineer", "Beta", "org-2", "2020-06", "2023-01"),
    ]
    r1 = _run_rule(StrongestExperienceRule(), exps)
    r2 = _run_rule(StrongestExperienceRule(), exps)
    assert r1[0].value == r2[0].value


# ===================================================================
# LeadershipExperienceRule
# ===================================================================


def test_leadership_empty() -> None:
    results = _run_rule(LeadershipExperienceRule(), [])
    assert results[0].value["has_leadership"] is False
    assert results[0].value["leadership_roles"] == []


def test_leadership_no_roles() -> None:
    exps = [_exp("e1", "Engineer", "Acme", "org-1")]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert results[0].value["has_leadership"] is False


def test_leadership_manager_detected() -> None:
    exps = [_exp("e1", "Engineering Manager", "Acme", "org-1")]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert results[0].value["has_leadership"]
    assert len(results[0].value["leadership_roles"]) == 1
    assert results[0].value["leadership_roles"][0]["role"] == "manager"


def test_leadership_director_detected() -> None:
    exps = [_exp("e1", "Director of Engineering", "Acme", "org-1")]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert results[0].value["has_leadership"]


def test_leadership_multiple_roles() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1"),
        _exp("e2", "Team Lead", "Beta", "org-2"),
        _exp("e3", "CTO", "Gamma", "org-3"),
    ]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert len(results[0].value["leadership_roles"]) == 2


def test_leadership_no_substring_false_positive() -> None:
    exps = [_exp("e1", "Director", "Acme", "org-1")]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert results[0].value["has_leadership"]


# ===================================================================
# CloudExperienceRule
# ===================================================================


def test_cloud_no_skills() -> None:
    results = _run_rule(CloudExperienceRule(), [])
    assert not results[0].value["has_cloud_experience"]
    for p in results[0].value["providers"].values():
        assert not p["detected"]


def test_cloud_aws_detected() -> None:
    skills = [_skill("s1", "AWS", "Cloud")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["has_cloud_experience"]
    assert results[0].value["providers"]["AWS"]["detected"]
    assert results[0].value["providers"]["AWS"]["skills"] == ["AWS"]
    assert results[0].value["providers"]["AWS"]["frequency"] == 1


def test_cloud_azure_detected() -> None:
    skills = [_skill("s1", "Azure Functions", "Cloud")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["providers"]["Azure"]["detected"]
    assert "Azure Functions" in results[0].value["providers"]["Azure"]["skills"]


def test_cloud_gcp_detected() -> None:
    skills = [_skill("s1", "Google Cloud Platform", "Cloud")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["providers"]["GCP"]["detected"]


def test_cloud_multiple_providers() -> None:
    skills = [
        _skill("s1", "AWS", "Cloud"),
        _skill("s2", "Azure", "Cloud"),
        _skill("s3", "BigQuery", "Cloud"),
    ]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["providers"]["AWS"]["detected"]
    assert results[0].value["providers"]["Azure"]["detected"]
    assert results[0].value["providers"]["GCP"]["detected"]


def test_cloud_first_and_recent_use() -> None:
    skills = [
        _skill("s1", "AWS", "Cloud", experience_ids=["e1", "e2"]),
    ]
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2019-01", "2021-01"),
        _exp("e2", "Senior Engineer", "Acme", "org-1", "2021-01", "2023-06"),
    ]
    results = _run_rule(CloudExperienceRule(), exps, skills=skills)
    aws = results[0].value["providers"]["AWS"]
    assert aws["first_use"] == "2019-01"
    assert aws["most_recent_use"] == "2023-06"
    assert aws["estimated_years"] is not None


def test_cloud_no_match() -> None:
    skills = [_skill("s1", "Python", "Language")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert not results[0].value["has_cloud_experience"]


def test_cloud_substring_no_false_positive() -> None:
    skills = [_skill("s1", "claws", "Tools")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert not results[0].value["has_cloud_experience"]


# ===================================================================
# TechnologyBreadthRule
# ===================================================================


def test_technology_breadth_empty() -> None:
    results = _run_rule(TechnologyBreadthRule(), [], skills=[])
    v = results[0].value
    assert v["total_technologies"] == 0
    assert v["categories"] == {}
    assert v["strongest_category"] is None
    assert v["weakest_category"] is None


def test_technology_breadth_single_category() -> None:
    skills = [
        _skill("s1", "Python", "Language"),
        _skill("s2", "JavaScript", "Language"),
    ]
    results = _run_rule(TechnologyBreadthRule(), [], skills=skills)
    v = results[0].value
    assert v["total_technologies"] == 2
    assert v["categories"]["Language"]["count"] == 2


def test_technology_breadth_multiple_categories() -> None:
    skills = [
        _skill("s1", "Python", "Language"),
        _skill("s2", "JavaScript", "Language"),
        _skill("s3", "AWS", "Cloud"),
        _skill("s4", "Django", "Framework"),
    ]
    results = _run_rule(TechnologyBreadthRule(), [], skills=skills)
    v = results[0].value
    assert v["total_technologies"] == 4
    assert v["strongest_category"] == "Language"
    assert v["weakest_category"] in ("Cloud", "Framework")


def test_technology_breadth_uncategorized() -> None:
    skills = [
        _skill("s1", "Python", ""),
        _skill("s2", "AWS", ""),
    ]
    results = _run_rule(TechnologyBreadthRule(), [], skills=skills)
    v = results[0].value
    assert "Uncategorized" in v["categories"]
    assert v["categories"]["Uncategorized"]["count"] == 2


def test_technology_breadth_deterministic() -> None:
    skills = [
        _skill("s1", "Python", "Language"),
        _skill("s2", "AWS", "Cloud"),
    ]
    r1 = _run_rule(TechnologyBreadthRule(), [], skills=skills)
    r2 = _run_rule(TechnologyBreadthRule(), [], skills=skills)
    assert r1[0].value == r2[0].value


# ===================================================================
# DomainExperienceRule
# ===================================================================


def test_domain_empty() -> None:
    results = _run_rule(DomainExperienceRule(), [])
    assert results[0].value == {}
    assert results[0].metadata["total_domains"] == 0


def test_domain_finance_detected() -> None:
    exps = [
        _exp("e1", "Engineer", "Big Bank Corp", "org-1", "2020-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    assert "Finance" in results[0].value
    assert results[0].value["Finance"]["years"] >= 2.9


def test_domain_healthcare_detected() -> None:
    exps = [
        _exp("e1", "Engineer", "HealthFirst Inc", "org-1", "2021-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    assert "Healthcare" in results[0].value


def test_domain_tech_detected_from_title() -> None:
    exps = [
        _exp("e1", "Software Engineer", "Acme Corp", "org-1", "2020-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    assert "Technology" in results[0].value


def test_domain_multiple_industries() -> None:
    exps = [
        _exp("e1", "Engineer", "Big Bank", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Engineer", "HealthFirst", "org-2", "2021-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    assert "Finance" in results[0].value
    assert "Healthcare" in results[0].value


def test_domain_no_match() -> None:
    exps = [
        _exp("e1", "Artist", "Creative Studio", "org-1", "2020-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    assert results[0].value == {}


def test_domain_organization_collected() -> None:
    exps = [
        _exp("e1", "Engineer", "Big Bank", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Analyst", "Big Bank", "org-1", "2021-01", "2023-01"),
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    finance = results[0].value.get("Finance", {})
    assert finance.get("organization_count", 0) >= 1
    assert "Big Bank" in finance.get("organizations", [])


# ===================================================================
# SeniorResponsibilityRule
# ===================================================================


def test_senior_responsibility_empty() -> None:
    results = _run_rule(SeniorResponsibilityRule(), [])
    assert results[0].metadata["areas_detected"] == []
    for area in results[0].value.values():
        assert not area["detected"]


def test_senior_responsibility_architecture() -> None:
    exps = [
        _exp("e1", "Software Architect", "Acme", "org-1", scope="System design"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["architecture"]["detected"]
    assert "architecture" in results[0].metadata["areas_detected"]


def test_senior_responsibility_devops() -> None:
    exps = [
        _exp("e1", "DevOps Engineer", "Acme", "org-1", scope="CI/CD pipeline"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["devops"]["detected"]


def test_senior_responsibility_migrations() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", scope="Cloud migration project"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["migrations"]["detected"]


def test_senior_responsibility_security() -> None:
    exps = [
        _exp("e1", "Security Engineer", "Acme", "org-1"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["security"]["detected"]


def test_senior_responsibility_multiple_areas() -> None:
    exps = [
        _exp("e1", "DevOps Architect", "Acme", "org-1", scope="Security compliance"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["architecture"]["detected"]
    assert results[0].value["devops"]["detected"]
    assert results[0].value["security"]["detected"]


def test_senior_responsibility_operations() -> None:
    exps = [
        _exp("e1", "SRE", "Acme", "org-1", scope="Production support"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["operations"]["detected"]


def test_senior_responsibility_mentoring() -> None:
    exps = [
        _exp("e1", "Team Lead", "Acme", "org-1"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["mentoring"]["detected"]


def test_senior_responsibility_platform() -> None:
    exps = [
        _exp("e1", "Platform Engineer", "Acme", "org-1"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].value["platform_ownership"]["detected"]


def test_senior_responsibility_no_match() -> None:
    exps = [
        _exp("e1", "Junior Engineer", "Acme", "org-1"),
    ]
    results = _run_rule(SeniorResponsibilityRule(), exps)
    assert results[0].metadata["areas_detected"] == []


# ===================================================================
# CareerHighlightsRule
# ===================================================================


def test_career_highlights_empty() -> None:
    results = _run_rule(CareerHighlightsRule(), [])
    assert results[0].value["longest_project"] is None
    assert results[0].value["highest_responsibility"] is None
    assert results[0].value["longest_employer"] is None
    assert results[0].value["largest_technology_stack"] is None
    assert results[0].value["migration_experience"] is None


def test_career_highlights_longest_project() -> None:
    exps = [
        _exp("e1", "Short", "Acme", "org-1", "2021-01", "2022-01"),
        _exp("e2", "Long", "Beta", "org-2", "2019-01", "2024-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    h = results[0].value["longest_project"]
    assert h["title"] == "Long"
    assert h["duration_years"] >= 4.9


def test_career_highlights_highest_responsibility() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Director", "Beta", "org-2", "2021-01", "2023-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    h = results[0].value["highest_responsibility"]
    assert h["title"] == "Director"
    assert h["title_level"] >= 4


def test_career_highlights_longest_employer() -> None:
    exps = [
        _exp("e1", "Role 1", "Acme Corp", "org-1", "2018-01", "2021-01"),
        _exp("e2", "Role 2", "Acme Corp", "org-1", "2021-01", "2024-01"),
        _exp("e3", "Role", "Beta Inc", "org-2", "2022-01", "2023-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    h = results[0].value["longest_employer"]
    assert h["organization"] == "Acme Corp"
    assert h["total_years"] >= 5.9
    assert h["role_count"] == 2


def test_career_highlights_largest_tech_stack() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Engineer", "Beta Inc", "org-2", "2021-01", "2023-01"),
    ]
    skills = [
        _skill("s1", "Python", "Language", experience_ids=["e1"]),
        _skill("s2", "AWS", "Cloud", experience_ids=["e1"]),
        _skill("s3", "Django", "Framework", experience_ids=["e1"]),
        _skill("s4", "Java", "Language", experience_ids=["e2"]),
    ]
    results = _run_rule(CareerHighlightsRule(), exps, skills=skills)
    h = results[0].value["largest_technology_stack"]
    assert h["organization"] == "Acme Corp"
    assert h["skill_count"] == 3
    assert "Python" in h["skills"]


def test_career_highlights_migration_experience() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Cloud Migration Lead", "Beta", "org-2", "2021-01", "2023-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    h = results[0].value["migration_experience"]
    assert h is not None
    assert h["title"] == "Cloud Migration Lead"


def test_career_highlights_migration_in_scope() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01",
             scope="Led cloud migration project"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    h = results[0].value["migration_experience"]
    assert h is not None


def test_career_highlights_migration_not_found() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    assert results[0].value["migration_experience"] is None


def test_career_highlights_deterministic() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Manager", "Beta Inc", "org-2", "2021-01", "2023-01"),
    ]
    skills = [
        _skill("s1", "Python", "Language", experience_ids=["e1"]),
    ]
    r1 = _run_rule(CareerHighlightsRule(), exps, skills=skills)
    r2 = _run_rule(CareerHighlightsRule(), exps, skills=skills)
    assert r1[0].value == r2[0].value


# ===================================================================
# Integration: all experience rules together
# ===================================================================


def test_all_experience_rules_together() -> None:
    from careeros.reasoning import ReasoningEngine as RE
    from careeros.reasoning import RuleRegistry as RR

    exps = [
            _exp(
                "e1",
                "Software Engineer",
                "Big Bank Corp",
                "org-bank",
                "2017-01",
                "2020-06",
                scope="Payment processing platform",
            ),
            _exp(
                "e2",
                "Senior DevOps Engineer",
                "Big Bank Corp",
                "org-bank",
                "2020-06",
                "2023-01",
                scope="AWS cloud migration, CI/CD pipelines",
            ),
            _exp(
                "e3",
                "Team Lead",
                "Tech Solutions Inc",
                "org-tech",
                "2023-06",
                is_current=True,
                scope="Platform architecture, mentoring",
            ),
        ]
    skills = [
        _skill("s1", "Python", "Language", experience_ids=["e1", "e2"]),
        _skill("s2", "AWS", "Cloud", experience_ids=["e2"]),
        _skill("s3", "Docker", "DevOps", experience_ids=["e2", "e3"]),
        _skill("s4", "Kubernetes", "DevOps", experience_ids=["e2", "e3"]),
        _skill("s5", "Java", "Language", experience_ids=["e1"]),
        _skill("s6", "Terraform", "DevOps", experience_ids=["e2"]),
    ]

    profile = _profile(experiences=exps, skills=skills)
    graph = KnowledgeGraphBuilder().build(profile)

    registry = RR()
    registry.register(StrongestExperienceRule())
    registry.register(LeadershipExperienceRule())
    registry.register(CloudExperienceRule())
    registry.register(TechnologyBreadthRule())
    registry.register(DomainExperienceRule())
    registry.register(SeniorResponsibilityRule())
    registry.register(CareerHighlightsRule())

    engine = RE(registry)
    analysis = engine.run(graph, profile=profile)

    findings = {r.finding_type: r for r in analysis.reasoning_results}
    assert len(findings) == 7

    # Strongest
    assert "strongest_experience" in findings
    assert len(findings["strongest_experience"].value) == 3
    assert findings["strongest_experience"].value[0]["has_leadership"]

    # Leadership
    assert "leadership_experience" in findings
    assert findings["leadership_experience"].value["has_leadership"]

    # Cloud
    assert "cloud_experience" in findings
    assert findings["cloud_experience"].value["has_cloud_experience"]
    assert findings["cloud_experience"].value["providers"]["AWS"]["detected"]

    # Tech breadth
    assert "technology_breadth" in findings
    assert findings["technology_breadth"].value["total_technologies"] == 6
    assert findings["technology_breadth"].value["strongest_category"] == "DevOps"

    # Domain
    assert "domain_experience" in findings
    assert len(findings["domain_experience"].value) >= 2

    # Senior responsibility
    assert "senior_responsibility" in findings
    detected = findings["senior_responsibility"].metadata["areas_detected"]
    assert "devops" in detected
    assert "migrations" in detected
    assert "mentoring" in detected

    # Highlights
    assert "career_highlights" in findings
    h = findings["career_highlights"].value
    assert h["longest_employer"]["organization"] == "Big Bank Corp"
    assert h["migration_experience"] is not None
    assert h["highest_responsibility"]["title"] in ("Senior DevOps Engineer", "Team Lead")

    assert analysis.execution_stats["total_rules"] == 7
    assert analysis.execution_stats["total_findings"] == 7


def test_all_experience_rules_deterministic() -> None:
    from careeros.reasoning import ReasoningEngine as RE
    from careeros.reasoning import RuleRegistry as RR

    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-1", "2020-01", "2023-01"),
    ]
    skills = [
        _skill("s1", "Python", "Language", experience_ids=["e1"]),
    ]
    profile = _profile(experiences=exps, skills=skills)
    graph = KnowledgeGraphBuilder().build(profile)

    registry = RR()
    registry.register(StrongestExperienceRule())
    registry.register(LeadershipExperienceRule())
    registry.register(CloudExperienceRule())
    registry.register(TechnologyBreadthRule())
    registry.register(DomainExperienceRule())
    registry.register(SeniorResponsibilityRule())
    registry.register(CareerHighlightsRule())

    engine = RE(registry)
    a1 = engine.run(graph, profile=profile)
    a2 = engine.run(graph, profile=profile)
    assert a1.reasoning_results == a2.reasoning_results


# ===================================================================
# Edge cases
# ===================================================================


def test_edge_case_no_organization_ref() -> None:
    exps = [
        {
            "id": "e1",
            "title": "Freelancer",
            "dateRange": {"start": "2020-01", "end": "2021-01"},
        }
    ]
    results = _run_rule(StrongestExperienceRule(), exps)
    assert len(results[0].value) == 1
    assert results[0].value[0]["organization"] == "Unknown Organization"


def test_edge_case_missing_title() -> None:
    exps = [
        {"id": "e1", "dateRange": {"start": "2020-01", "end": "2021-01"}},
    ]
    results = _run_rule(StrongestExperienceRule(), exps)
    assert len(results[0].value) == 1


def test_edge_case_empty_title_for_leadership() -> None:
    exps = [
        _exp("e1", "", "Acme", "org-1"),
    ]
    results = _run_rule(LeadershipExperienceRule(), exps)
    assert not results[0].value["has_leadership"]


def test_edge_case_skill_without_experience_evidence() -> None:
    skills = [_skill("s1", "AWS", "Cloud")]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["has_cloud_experience"]
    # No experience IDs linked, so first_use etc should be None
    aws = results[0].value["providers"]["AWS"]
    assert aws["first_use"] is None
    assert aws["most_recent_use"] is None


def test_edge_case_skills_no_experience_link() -> None:
    skills = [
        _skill("s1", "AWS", "Cloud"),
        _skill("s2", "Azure", "Cloud"),
    ]
    results = _run_rule(CloudExperienceRule(), [], skills=skills)
    assert results[0].value["has_cloud_experience"]
    assert results[0].value["providers"]["AWS"]["detected"]
    assert results[0].value["providers"]["Azure"]["detected"]


def test_edge_case_domain_no_org_ref() -> None:
    exps = [
        {
            "id": "e1",
            "title": "Software Engineer",
            "dateRange": {"start": "2020-01", "end": "2021-01"},
        }
    ]
    results = _run_rule(DomainExperienceRule(), exps)
    # "Software" keyword in title triggers Technology industry
    assert "Technology" in results[0].value
    assert results[0].value["Technology"]["organizations"] == ["Unknown Organization"]


def test_edge_case_no_skills_for_highlights() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
    ]
    results = _run_rule(CareerHighlightsRule(), exps)
    assert results[0].value["largest_technology_stack"] is None


def test_edge_case_all_confidence_one() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme", "org-1", "2020-01", "2023-01"),
    ]
    skills = [_skill("s1", "Python", "Language")]

    for rule_cls in [
        StrongestExperienceRule,
        LeadershipExperienceRule,
        CloudExperienceRule,
        TechnologyBreadthRule,
        DomainExperienceRule,
        SeniorResponsibilityRule,
        CareerHighlightsRule,
    ]:
        results = _run_rule(rule_cls(), exps, skills=skills)
        for r in results:
            assert r.confidence == 1.0, f"{rule_cls.__name__} confidence != 1.0"
