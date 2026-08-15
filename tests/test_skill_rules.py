from __future__ import annotations

from typing import Any

import pytest

from careeros.knowledge import KnowledgeGraphBuilder
from careeros.reasoning import ReasoningEngine, ReasoningResult, RuleContext
from careeros.reasoning.rules import (
    CoreCompetenciesRule,
    EmergingSkillsRule,
    RareSkillsRule,
    SkillCategoryBalanceRule,
    SkillEvidenceStrengthRule,
    SkillProgressionRule,
    SpecializedSkillsRule,
    StrongestSkillsRule,
    TransferableSkillsRule,
)
from careeros.reasoning.rules.skill_rules import (
    SKILL_CATEGORIES,
    _categorize_skill,
    _collect_skill_data,
    _is_rare_skill,
    _is_specialized_skill,
    _is_transferable_skill,
    _resolve_proficiency,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    person_id: str = "person-test",
    skills: list[dict[str, Any]] | None = None,
    experiences: list[dict[str, Any]] | None = None,
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


def _skill(
    sid: str,
    name: str,
    category: str = "",
    experiences: list[dict[str, Any]] | None = None,
    proficiency: str = "",
) -> dict[str, Any]:
    skill: dict[str, Any] = {
        "id": sid,
        "name": name,
        "category": category,
    }
    exts: dict[str, Any] = {}
    if proficiency:
        exts["proficiency"] = proficiency
    if experiences:
        exts["experienceEvidence"] = [
            {"experienceId": e["id"]} for e in experiences
        ]
    if exts:
        skill["extensions"] = exts
    return skill


def _exp(
    eid: str,
    title: str,
    org_name: str,
    org_id: str,
    start: str | None = None,
    end: str | None = None,
    is_current: bool = False,
    scope: str = "",
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
    exp["organizationRefs"] = [{"id": org_id, "name": org_name}]
    if scope:
        exp["scope"] = scope
    return exp


def _rule_context(profile: dict) -> RuleContext:
    graph = KnowledgeGraphBuilder().build(profile)
    return RuleContext(graph=graph, profile=profile, parameters={})


def _execute(rule: Any, profile: dict) -> list[ReasoningResult]:
    ctx = _rule_context(profile)
    return rule.execute(ctx)


# ===================================================================
# Lookup table tests
# ===================================================================


def test_categorize_skill_programming() -> None:
    assert _categorize_skill("Python") == "Programming"
    assert _categorize_skill("Java") == "Programming"
    assert _categorize_skill("javascript") == "Programming"


def test_categorize_skill_cloud() -> None:
    assert _categorize_skill("AWS") == "Cloud"
    assert _categorize_skill("azure functions") == "Cloud"


def test_categorize_skill_devops() -> None:
    assert _categorize_skill("Docker") == "DevOps"
    assert _categorize_skill("jenkins") == "DevOps"
    assert _categorize_skill("kubernetes") == "DevOps"


def test_categorize_skill_unknown() -> None:
    assert _categorize_skill("SomeRandomSkill123") is None


def test_categorize_skill_case_insensitive() -> None:
    assert _categorize_skill("PYTHON") == "Programming"
    assert _categorize_skill("Aws") == "Cloud"


def test_is_rare_skill_true() -> None:
    assert _is_rare_skill("COBOL") is True
    assert _is_rare_skill("mainframe") is True
    assert _is_rare_skill("blockchain") is True


def test_is_rare_skill_false() -> None:
    assert _is_rare_skill("Python") is False
    assert _is_rare_skill("Kubernetes") is False


def test_is_transferable_skill_true() -> None:
    assert _is_transferable_skill("leadership") is True
    assert _is_transferable_skill("project management") is True
    assert _is_transferable_skill("system design") is True


def test_is_transferable_skill_false() -> None:
    assert _is_transferable_skill("Kubernetes") is False
    assert _is_transferable_skill("Python") is False


def test_resolve_proficiency_known() -> None:
    assert _resolve_proficiency("beginner") == 1
    assert _resolve_proficiency("intermediate") == 2
    assert _resolve_proficiency("advanced") == 4
    assert _resolve_proficiency("expert") == 5


def test_resolve_proficiency_unknown_defaults_to_intermediate() -> None:
    assert _resolve_proficiency("guru") == 2
    assert _resolve_proficiency("") == 2
    assert _resolve_proficiency(None) == 2


def test_resolve_proficiency_case_insensitive() -> None:
    assert _resolve_proficiency("Advanced") == 4
    assert _resolve_proficiency("EXPERT") == 5


# ===================================================================
# StrongestSkillsRule
# ===================================================================


def test_strongest_skills_empty() -> None:
    rule = StrongestSkillsRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].finding_type == "strongest_skills"
    assert results[0].value == []
    assert results[0].metadata["total_skills_analyzed"] == 0


def test_strongest_skills_single() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
        experiences=[_exp("e1", "Engineer", "Corp", "org-1", "2020-01", "2023-01")],
    )
    ctx = _rule_context(profile)
    rule = StrongestSkillsRule()
    results = rule.execute(ctx)
    assert len(results) == 1
    ranked = results[0].value
    assert len(ranked) == 1
    assert ranked[0]["name"] == "Python"
    assert ranked[0]["score"] > 0


def test_strongest_skills_ranking() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming",
                   experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")]),
            _skill("s2", "Kubernetes", "DevOps",
                   experiences=[_exp("e2", "DevOps", "Corp", "org-1", "2021-01", "2023-01"),
                                _exp("e3", "SRE", "Other", "org-2", "2022-01", "2023-01")]),
        ],
        experiences=[
            _exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01"),
            _exp("e2", "DevOps", "Corp", "org-1", "2021-01", "2023-01"),
            _exp("e3", "SRE", "Other", "org-2", "2022-01", "2023-01"),
        ],
    )
    ctx = _rule_context(profile)
    rule = StrongestSkillsRule()
    results = rule.execute(ctx)
    ranked = results[0].value
    assert len(ranked) == 2
    assert ranked[0]["name"] == "Kubernetes"
    assert ranked[1]["name"] == "Python"
    assert ranked[0]["score"] >= ranked[1]["score"]


def test_strongest_skills_deterministic() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming"),
                _skill("s2", "Java", "Programming")],
    )
    rule = StrongestSkillsRule()
    results1 = _execute(rule, profile)
    results2 = _execute(rule, profile)
    assert results1[0].value == results2[0].value


def test_strongest_skills_with_proficiency() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming", proficiency="advanced"),
            _skill("s2", "Java", "Programming", proficiency="beginner"),
        ],
    )
    ctx = _rule_context(profile)
    rule = StrongestSkillsRule()
    results = rule.execute(ctx)
    ranked = results[0].value
    assert ranked[0]["name"] == "Python"
    assert ranked[0]["proficiency"] == 4
    assert ranked[1]["name"] == "Java"
    assert ranked[1]["proficiency"] == 1


def test_strongest_skills_metadata() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    rule = StrongestSkillsRule()
    results = _execute(rule, profile)
    meta = results[0].metadata
    assert meta["total_skills_analyzed"] == 1
    assert meta["top_skill"] == "Python"
    assert meta["top_score"] > 0


# ===================================================================
# EmergingSkillsRule
# ===================================================================


def test_emerging_skills_empty() -> None:
    rule = EmergingSkillsRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []
    assert results[0].metadata["emerging_count"] == 0


def test_emerging_skills_requires_recent_first_use() -> None:
    skill_exp = _exp("e1", "DevOps", "Corp", "org-1", "2025-06")
    skills_data = [_skill("s1", "Docker", "DevOps", experiences=[skill_exp])]
    exps = [skill_exp]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = EmergingSkillsRule()
    results = _execute(rule, profile)
    emerging = results[0].value
    assert len(emerging) == 1
    assert emerging[0]["name"] == "Docker"


def test_emerging_skills_old_skill_not_emerging() -> None:
    skill_exp = _exp("e1", "Dev", "Corp", "org-1", "2018-01")
    skills_data = [_skill("s1", "Python", "Programming", experiences=[skill_exp])]
    exps = [skill_exp]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = EmergingSkillsRule()
    results = _execute(rule, profile)
    assert results[0].value == []


def test_emerging_skills_metadata() -> None:
    skill_exp = _exp("e1", "Dev", "Corp", "org-1", "2025-06")
    skills_data = [_skill("s1", "Rust", "Programming", experiences=[skill_exp])]
    exps = [skill_exp]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = EmergingSkillsRule()
    results = _execute(rule, profile)
    meta = results[0].metadata
    assert meta["emerging_count"] == 1
    assert meta["threshold_years"] == 2.0


# ===================================================================
# CoreCompetenciesRule
# ===================================================================


def test_core_competencies_empty() -> None:
    rule = CoreCompetenciesRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []


def test_core_competencies_no_skills() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    rule = CoreCompetenciesRule()
    results = _execute(rule, profile)
    assert results[0].value == []


def test_core_competencies_with_experience() -> None:
    skills_data = [_skill("s1", "Python", "Programming")]
    exps = [
        _exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01"),
        _exp("e2", "Engineer", "Other", "org-2", "2021-06", "2024-06"),
    ]
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming",
                       experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")])],
        experiences=exps,
    )
    rule = CoreCompetenciesRule()
    results = _execute(rule, profile)
    # Skill has no experience evidence linking to org-2, so it only sees 1 org
    core = results[0].value
    # Even without multi-org, single employer with >2 years still qualifies
    assert len(core) == 1
    assert core[0]["name"] == "Python"
    assert core[0]["breadth"] == "single_employer"


def test_core_competencies_multi_employer() -> None:
    skills_data = [
        _skill("s1", "Python", "Programming",
               experiences=[_exp("e1", "Dev", "Corp1", "org-1", "2020-01", "2022-01"),
                            _exp("e2", "Sr Dev", "Corp2", "org-2", "2022-06", "2024-06")]),
    ]
    exps = [
        _exp("e1", "Dev", "Corp1", "org-1", "2020-01", "2022-01"),
        _exp("e2", "Sr Dev", "Corp2", "org-2", "2022-06", "2024-06"),
    ]
    profile = _profile(
        skills=skills_data,
        experiences=exps,
    )
    rule = CoreCompetenciesRule()
    results = _execute(rule, profile)
    core = results[0].value
    assert len(core) == 1
    assert core[0]["breadth"] == "multi_employer"


def test_core_competencies_sustained_depth() -> None:
    skills_data = [_skill("s1", "Python", "Programming")]
    exps = [_exp("e1", "Dev", "Corp", "org-1", "2018-01", "2024-01")]
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming",
                       experiences=[_exp("e1", "Dev", "Corp", "org-1", "2018-01", "2024-01")])],
        experiences=exps,
    )
    rule = CoreCompetenciesRule()
    results = _execute(rule, profile)
    core = results[0].value
    assert len(core) == 1
    assert core[0]["depth"] == "sustained"


# ===================================================================
# SkillCategoryBalanceRule
# ===================================================================


def test_skill_category_balance_empty() -> None:
    rule = SkillCategoryBalanceRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    val = results[0].value
    assert val["total_categories"] == 0
    assert val["strongest_category"] is None
    assert val["weakest_category"] is None


def test_skill_category_balance_single_category() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming"),
            _skill("s2", "Java", "Programming"),
        ],
    )
    rule = SkillCategoryBalanceRule()
    results = _execute(rule, profile)
    val = results[0].value
    assert val["total_categories"] == 1
    assert val["strongest_category"] == "Programming"
    assert val["weakest_category"] == "Programming"


def test_skill_category_balance_multiple_categories() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming"),
            _skill("s2", "AWS", "Cloud"),
            _skill("s3", "Docker", "DevOps"),
            _skill("s4", "Java", "Programming"),
        ],
    )
    rule = SkillCategoryBalanceRule()
    results = _execute(rule, profile)
    val = results[0].value
    assert val["total_categories"] == 3
    assert val["strongest_category"] == "Programming"
    assert "categories" in val
    assert "balance_metric" in val


def test_skill_category_balance_uncategorized() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python"),
            _skill("s2", "AWS"),
        ],
    )
    rule = SkillCategoryBalanceRule()
    results = _execute(rule, profile)
    val = results[0].value
    assert val["total_categories"] >= 1


def test_skill_category_balance_deterministic() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming"),
            _skill("s2", "AWS", "Cloud"),
        ],
    )
    rule = SkillCategoryBalanceRule()
    results1 = _execute(rule, profile)
    results2 = _execute(rule, profile)
    assert results1[0].value == results2[0].value


# ===================================================================
# SkillEvidenceStrengthRule
# ===================================================================


def test_skill_evidence_strength_empty() -> None:
    rule = SkillEvidenceStrengthRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []


def test_skill_evidence_strength_single_skill_no_experience() -> None:
    profile = _profile(skills=[_skill("s1", "Python", "Programming")])
    rule = SkillEvidenceStrengthRule()
    results = _execute(rule, profile)
    strengths = results[0].value
    assert len(strengths) == 1
    assert strengths[0]["confidence"] < 0.5


def test_skill_evidence_strength_with_experience() -> None:
    skills_data = [_skill("s1", "Python", "Programming",
                          experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")])]
    exps = [_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = SkillEvidenceStrengthRule()
    results = _execute(rule, profile)
    strengths = results[0].value
    assert len(strengths) == 1
    assert strengths[0]["label"] in ("low", "medium", "high", "very_high")


def test_skill_evidence_strength_multi_experience_higher_confidence() -> None:
    skills_multi = [_skill("s1", "Python", "Programming",
                           experiences=[_exp("e1", "Dev", "Corp1", "org-1", "2020-01", "2022-01"),
                                        _exp("e2", "Sr Dev", "Corp2", "org-2", "2022-06", "2024-06")])]
    exps = [
        _exp("e1", "Dev", "Corp1", "org-1", "2020-01", "2022-01"),
        _exp("e2", "Sr Dev", "Corp2", "org-2", "2022-06", "2024-06"),
    ]
    profile_multi = _profile(skills=skills_multi, experiences=exps)

    skills_single = [_skill("s1", "Python", "Programming",
                            experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")])]
    exps_single = [_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")]
    profile_single = _profile(skills=skills_single, experiences=exps_single)

    rule = SkillEvidenceStrengthRule()
    results_multi = _execute(rule, profile_multi)
    results_single = _execute(rule, profile_single)
    assert results_multi[0].value[0]["confidence"] > results_single[0].value[0]["confidence"]


def test_skill_evidence_strength_very_high_confidence() -> None:
    skills_data = [_skill("s1", "Python", "Programming",
                           experiences=[
                               _exp("e1", "Dev", "Corp1", "org-1", "2018-01", "2020-01"),
                               _exp("e2", "Sr Dev", "Corp2", "org-2", "2020-06", "2022-01"),
                               _exp("e3", "Architect", "Corp3", "org-3", "2022-06", "2024-01"),
                               _exp("e4", "Lead", "Corp3", "org-3", "2019-06", "2024-06"),
                           ])]
    exps = [
        _exp("e1", "Dev", "Corp1", "org-1", "2018-01", "2020-01"),
        _exp("e2", "Sr Dev", "Corp2", "org-2", "2020-06", "2022-01"),
        _exp("e3", "Architect", "Corp3", "org-3", "2022-06", "2024-01"),
        _exp("e4", "Lead", "Corp3", "org-3", "2019-06", "2024-06"),
    ]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = SkillEvidenceStrengthRule()
    results = _execute(rule, profile)
    strengths = results[0].value
    assert len(strengths) == 1
    assert strengths[0]["confidence"] >= 0.8
    assert strengths[0]["label"] == "very_high"


def test_skill_evidence_strength_metadata() -> None:
    profile = _profile(skills=[_skill("s1", "Python", "Programming")])
    rule = SkillEvidenceStrengthRule()
    results = _execute(rule, profile)
    assert results[0].metadata["total_skills_analyzed"] == 1


# ===================================================================
# RareSkillsRule
# ===================================================================


def test_rare_skills_empty() -> None:
    rule = RareSkillsRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []


def test_rare_skills_no_rare() -> None:
    profile = _profile(skills=[
        _skill("s1", "Python", "Programming"),
        _skill("s2", "Kubernetes", "DevOps"),
    ])
    rule = RareSkillsRule()
    results = _execute(rule, profile)
    assert results[0].value == []


def test_rare_skills_detected() -> None:
    profile = _profile(skills=[
        _skill("s1", "Python", "Programming"),
        _skill("s2", "COBOL", "Programming"),
        _skill("s3", "mainframe", "Infrastructure"),
    ])
    rule = RareSkillsRule()
    results = _execute(rule, profile)
    rare = results[0].value
    assert len(rare) == 2
    names = {r["name"] for r in rare}
    assert "COBOL" in names
    assert "mainframe" in names


def test_rare_skills_metadata() -> None:
    profile = _profile(skills=[
        _skill("s1", "COBOL", "Programming"),
        _skill("s2", "Python", "Programming"),
    ])
    rule = RareSkillsRule()
    results = _execute(rule, profile)
    meta = results[0].metadata
    assert meta["rare_count"] == 1
    assert meta["total_skills_analyzed"] == 2


# ===================================================================
# SpecializedSkillsRule
# ===================================================================


def test_specialized_skills_empty() -> None:
    rule = SpecializedSkillsRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []


def test_specialized_skills_no_match() -> None:
    profile = _profile(skills=[
        _skill("s1", "Python", "Programming"),
        _skill("s2", "Leadership", "Leadership"),
    ])
    rule = SpecializedSkillsRule()
    results = _execute(rule, profile)
    assert results[0].value == []


def test_specialized_skills_detected() -> None:
    profile = _profile(skills=[
        _skill("s1", "Kubernetes", "DevOps"),
        _skill("s2", "Python", "Programming"),
        _skill("s3", "Terraform", "DevOps"),
    ])
    rule = SpecializedSkillsRule()
    results = _execute(rule, profile)
    specialized = results[0].value
    assert len(specialized) >= 2
    names = {s["name"] for s in specialized}
    assert "Kubernetes" in names
    assert "Terraform" in names


def test_specialized_skills_full_list() -> None:
    profile = _profile(skills=[
        _skill("s1", "Kubernetes", "DevOps"),
        _skill("s2", "Terraform", "DevOps"),
        _skill("s3", "OpenTelemetry", "Monitoring"),
        _skill("s4", "IAM", "Security"),
        _skill("s5", "VMware", "Infrastructure"),
        _skill("s6", "Kafka", "Databases"),
        _skill("s7", "Python", "Programming"),
    ])
    rule = SpecializedSkillsRule()
    results = _execute(rule, profile)
    specialized = results[0].value
    names = {s["name"] for s in specialized}
    for expected in ("Kubernetes", "Terraform", "OpenTelemetry", "IAM", "VMware", "Kafka"):
        assert expected in names


def test_specialized_skills_is_specialized_utility() -> None:
    assert _is_specialized_skill("Kubernetes") is True
    assert _is_specialized_skill("terraform") is True
    assert _is_specialized_skill("Python") is False
    assert _is_specialized_skill("Leadership") is False


def test_specialized_skills_metadata() -> None:
    profile = _profile(skills=[
        _skill("s1", "Kubernetes", "DevOps"),
        _skill("s2", "Python", "Programming"),
    ])
    rule = SpecializedSkillsRule()
    results = _execute(rule, profile)
    meta = results[0].metadata
    assert meta["specialized_count"] == 1
    assert meta["total_skills_analyzed"] == 2


def test_specialized_skills_with_experience() -> None:
    skills_data = [_skill("s1", "Kubernetes", "DevOps",
                          experiences=[_exp("e1", "DevOps", "Corp", "org-1", "2021-01", "2024-01")])]
    exps = [_exp("e1", "DevOps", "Corp", "org-1", "2021-01", "2024-01")]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = SpecializedSkillsRule()
    results = _execute(rule, profile)
    specialized = results[0].value
    assert len(specialized) == 1
    assert specialized[0]["name"] == "Kubernetes"
    assert specialized[0]["total_years"] > 0
    assert specialized[0]["experience_count"] == 1


def test_specialized_skills_deterministic() -> None:
    profile = _profile(skills=[
        _skill("s1", "Kubernetes", "DevOps"),
        _skill("s2", "Terraform", "DevOps"),
    ])
    rule = SpecializedSkillsRule()
    results1 = _execute(rule, profile)
    results2 = _execute(rule, profile)
    assert results1[0].value == results2[0].value


# ===================================================================
# TransferableSkillsRule
# ===================================================================


def test_transferable_skills_empty() -> None:
    rule = TransferableSkillsRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    assert results[0].value == []


def test_transferable_skills_no_transferable() -> None:
    profile = _profile(skills=[
        _skill("s1", "Kubernetes", "DevOps"),
        _skill("s2", "Terraform", "DevOps"),
    ])
    rule = TransferableSkillsRule()
    results = _execute(rule, profile)
    assert results[0].value == []


def test_transferable_skills_detected() -> None:
    profile = _profile(skills=[
        _skill("s1", "Python", "Programming"),
        _skill("s2", "leadership", "Leadership"),
        _skill("s3", "system design", "Architecture"),
    ])
    rule = TransferableSkillsRule()
    results = _execute(rule, profile)
    transferable = results[0].value
    assert len(transferable) >= 2
    names = {t["name"] for t in transferable}
    assert "leadership" in names
    assert "system design" in names


def test_transferable_skills_metadata() -> None:
    profile = _profile(skills=[
        _skill("s1", "leadership", "Leadership"),
        _skill("s2", "Python", "Programming"),
    ])
    rule = TransferableSkillsRule()
    results = _execute(rule, profile)
    assert results[0].metadata["transferable_count"] == 1


# ===================================================================
# SkillProgressionRule
# ===================================================================


def test_skill_progression_empty() -> None:
    rule = SkillProgressionRule()
    results = _execute(rule, _profile())
    assert len(results) == 1
    val = results[0].value
    assert val["stage"] == "foundation"
    assert val["total_skills"] == 0


def test_skill_progression_foundation() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    rule = SkillProgressionRule()
    results = _execute(rule, profile)
    assert results[0].value["stage"] == "foundation"


def test_skill_progression_intermediate() -> None:
    skills_data = [
        _skill("s1", "Python", "Programming",
               experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")]),
        _skill("s2", "AWS", "Cloud",
               experiences=[_exp("e2", "DevOps", "Corp2", "org-2", "2021-01", "2023-01")]),
        _skill("s3", "Docker", "DevOps",
               experiences=[_exp("e3", "DevOps", "Corp3", "org-3", "2021-06", "2023-01")]),
        _skill("s4", "Java", "Programming",
               experiences=[_exp("e4", "Dev", "Corp4", "org-4", "2020-06", "2022-01")]),
        _skill("s5", "SQL", "Databases",
               experiences=[_exp("e5", "Dev", "Corp5", "org-5", "2019-01", "2021-01")]),
    ]
    exps = [
        _exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01"),
        _exp("e2", "DevOps", "Corp2", "org-2", "2021-01", "2023-01"),
        _exp("e3", "DevOps", "Corp3", "org-3", "2021-06", "2023-01"),
        _exp("e4", "Dev", "Corp4", "org-4", "2020-06", "2022-01"),
        _exp("e5", "Dev", "Corp5", "org-5", "2019-01", "2021-01"),
    ]
    profile = _profile(skills=skills_data, experiences=exps)
    rule = SkillProgressionRule()
    results = _execute(rule, profile)
    assert results[0].value["stage"] in ("foundation", "intermediate", "advanced", "expert")


def test_skill_progression_metadata() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    rule = SkillProgressionRule()
    results = _execute(rule, profile)
    meta = results[0].metadata
    assert "stage" in meta
    assert meta["total_skills"] == 1


def test_skill_progression_deterministic() -> None:
    skills_data = [
        _skill("s1", "Python", "Programming"),
        _skill("s2", "Java", "Programming"),
        _skill("s3", "SQL", "Databases"),
    ]
    profile = _profile(skills=skills_data)
    rule = SkillProgressionRule()
    results1 = _execute(rule, profile)
    results2 = _execute(rule, profile)
    assert results1[0].value == results2[0].value


# ===================================================================
# Integration: all rules execute via engine
# ===================================================================


def test_all_skill_rules_together() -> None:
    from careeros.reasoning import ReasoningEngine
    from careeros.reasoning import RuleRegistry

    registry = RuleRegistry()
    registry.register(StrongestSkillsRule())
    registry.register(EmergingSkillsRule())
    registry.register(CoreCompetenciesRule())
    registry.register(SkillCategoryBalanceRule())
    registry.register(SkillEvidenceStrengthRule())
    registry.register(RareSkillsRule())
    registry.register(SpecializedSkillsRule())
    registry.register(TransferableSkillsRule())
    registry.register(SkillProgressionRule())

    engine = ReasoningEngine(registry)
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming",
                   experiences=[_exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01")]),
            _skill("s2", "AWS", "Cloud",
                   experiences=[_exp("e2", "DevOps", "Corp", "org-1", "2021-01", "2023-01")]),
            _skill("s3", "COBOL", "Programming",
                   experiences=[_exp("e3", "Mainframe", "Bank", "org-2", "2022-01", "2023-01")]),
            _skill("s4", "Kubernetes", "DevOps",
                   experiences=[_exp("e4", "DevOps", "Corp", "org-1", "2021-01", "2024-01")]),
        ],
        experiences=[
            _exp("e1", "Dev", "Corp", "org-1", "2020-01", "2023-01"),
            _exp("e2", "DevOps", "Corp", "org-1", "2021-01", "2023-01"),
            _exp("e3", "Mainframe", "Bank", "org-2", "2022-01", "2023-01"),
            _exp("e4", "DevOps", "Corp", "org-1", "2021-01", "2024-01"),
        ],
    )

    report = engine.analyze(profile)
    assert report.profile_id == "person-test"

    findings = {f.finding_type: f.value for f in report.findings}
    assert "strongest_skills" in findings
    assert "emerging_skills" in findings
    assert "core_competencies" in findings
    assert "skill_category_balance" in findings
    assert "skill_evidence_strength" in findings
    assert "rare_skills" in findings
    assert "specialized_skills" in findings
    assert "transferable_skills" in findings
    assert "skill_progression" in findings

    assert len(findings["strongest_skills"]) > 0
    assert len(findings["rare_skills"]) == 1  # COBOL
    assert "COBOL" in findings["rare_skills"][0]["name"]
    assert len(findings["specialized_skills"]) >= 1  # Kubernetes


def test_all_skill_rules_deterministic() -> None:
    from careeros.reasoning import ReasoningEngine
    from careeros.reasoning import RuleRegistry

    registry = RuleRegistry()
    registry.register(StrongestSkillsRule())
    registry.register(EmergingSkillsRule())
    registry.register(CoreCompetenciesRule())
    registry.register(SkillCategoryBalanceRule())
    registry.register(SkillEvidenceStrengthRule())
    registry.register(RareSkillsRule())
    registry.register(SpecializedSkillsRule())
    registry.register(TransferableSkillsRule())
    registry.register(SkillProgressionRule())

    engine = ReasoningEngine(registry)
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming"),
            _skill("s2", "AWS", "Cloud"),
        ],
    )

    report1 = engine.analyze(profile)
    report2 = engine.analyze(profile)
    d1 = report1.to_dict()
    d2 = report2.to_dict()
    assert d1["findings"] == d2["findings"]
    assert d1["findings_by_type"] == d2["findings_by_type"]
    assert d1["summary"]["total_findings"] == d2["summary"]["total_findings"]


def test_all_skill_rules_confidence_is_one() -> None:
    non_evidence_rules = [
        StrongestSkillsRule(),
        EmergingSkillsRule(),
        CoreCompetenciesRule(),
        SkillCategoryBalanceRule(),
        RareSkillsRule(),
        SpecializedSkillsRule(),
        TransferableSkillsRule(),
        SkillProgressionRule(),
    ]
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )

    for rule in non_evidence_rules:
        ctx = _rule_context(profile)
        results = rule.execute(ctx)
        for r in results:
            assert r.confidence == 1.0, f"{rule.id} has confidence != 1.0"

    rule = SkillEvidenceStrengthRule()
    results = rule.execute(_rule_context(profile))
    for r in results:
        assert 0.0 <= r.confidence <= 1.0
        assert r.metadata["provenance"] in ("full", "partial", "none")
        assert r.metadata["evidence_confidence_grade"] in (
            "very_low", "low", "medium", "high", "very_high",
        )


# ===================================================================
# Serialization compatibility
# ===================================================================


def test_skill_findings_in_reasoning_report_to_dict() -> None:
    from careeros.reasoning import ReasoningEngine
    from careeros.reasoning import RuleRegistry

    registry = RuleRegistry()
    registry.register(StrongestSkillsRule())
    registry.register(SkillCategoryBalanceRule())

    engine = ReasoningEngine(registry)
    profile = _profile(
        skills=[
            _skill("s1", "Python", "Programming"),
            _skill("s2", "Java", "Programming"),
        ],
    )
    report = engine.analyze(profile)
    d = report.to_dict()
    finding_types = {f["finding_type"] for f in d["findings"]}
    assert "strongest_skills" in finding_types
    assert "skill_category_balance" in finding_types
    assert d["summary"]["total_findings"] == 2


def test_skill_findings_in_reasoning_report_to_json() -> None:
    from careeros.reasoning import ReasoningEngine
    from careeros.reasoning import RuleRegistry
    import json

    registry = RuleRegistry()
    registry.register(StrongestSkillsRule())

    engine = ReasoningEngine(registry)
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    report = engine.analyze(profile)
    raw = report.to_json()
    parsed = json.loads(raw)
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["finding_type"] == "strongest_skills"


# ===================================================================
# Edge cases
# ===================================================================


def test_skill_with_experience_no_date_range() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming",
                       experiences=[_exp("e1", "Dev", "Corp", "org-1")])],
        experiences=[_exp("e1", "Dev", "Corp", "org-1")],
    )
    rule = StrongestSkillsRule()
    results = _execute(rule, profile)
    assert len(results[0].value) == 1


def test_skill_with_no_proficiency_default() -> None:
    profile = _profile(skills=[_skill("s1", "Python", "Programming")])
    rule = StrongestSkillsRule()
    results = _execute(rule, profile)
    assert results[0].value[0]["proficiency"] == 2


def test_category_from_profile_overrides_lookup() -> None:
    profile = _profile(skills=[
        _skill("s1", "Python", "CustomCategory"),
    ])
    ctx = _rule_context(profile)
    data = _collect_skill_data(ctx)
    assert data[0]["category"] == "CustomCategory"


def test_skills_with_same_score_deterministic_order() -> None:
    profile = _profile(
        skills=[
            _skill("s1", "Alpha", "Programming"),
            _skill("s2", "Beta", "Programming"),
        ],
    )
    rule = StrongestSkillsRule()
    results = _execute(rule, profile)
    ranked = results[0].value
    assert ranked[0]["name"] == "Alpha"
    assert ranked[1]["name"] == "Beta"


def test_all_rule_ids_are_unique() -> None:
    ids = [
        StrongestSkillsRule().id,
        EmergingSkillsRule().id,
        CoreCompetenciesRule().id,
        SkillCategoryBalanceRule().id,
        SkillEvidenceStrengthRule().id,
        RareSkillsRule().id,
        SpecializedSkillsRule().id,
        TransferableSkillsRule().id,
        SkillProgressionRule().id,
    ]
    assert len(ids) == len(set(ids))


def test_all_finding_types_are_unique() -> None:
    from careeros.reasoning.rules import StrongestSkillsRule
    sample_rules = [
        StrongestSkillsRule(),
        EmergingSkillsRule(),
        CoreCompetenciesRule(),
        SkillCategoryBalanceRule(),
        SkillEvidenceStrengthRule(),
        RareSkillsRule(),
        SpecializedSkillsRule(),
        TransferableSkillsRule(),
        SkillProgressionRule(),
    ]
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    types = []
    for rule in sample_rules:
        ctx = _rule_context(profile)
        for r in rule.execute(ctx):
            types.append(r.finding_type)
    assert len(types) == len(set(types)), f"Duplicate finding types: {types}"


def test_evidence_refs_contain_skill_ids() -> None:
    profile = _profile(
        skills=[_skill("s1", "Python", "Programming")],
    )
    rule = StrongestSkillsRule()
    results = _execute(rule, profile)
    refs = results[0].evidence_refs
    assert "s1" in refs


def test_empty_skills_no_evidence_refs() -> None:
    rule = StrongestSkillsRule()
    results = _execute(rule, _profile())
    assert results[0].evidence_refs == ()
