from datetime import datetime, timezone
from typing import Any

import pytest

from careeros.knowledge import KnowledgeGraphBuilder
from careeros.reasoning import ReasoningEngine, ReasoningResult, RuleContext
from careeros.reasoning.rules import (
    CareerProgressionRule,
    CareerStageRule,
    CurrentEmployerRule,
    CurrentRoleRule,
    EmploymentGapRule,
    LongestTenureRule,
    TotalYearsExperienceRule,
)
from careeros.reasoning.rules.tenure_rules import _org_name_and_id
from careeros.reasoning.utils import (
    duration_years,
    employment_gaps,
    format_duration,
    merge_overlapping_periods,
    parse_date,
    parse_date_range,
    title_level,
    total_experience_years,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    person_id: str = "person-test",
    experiences: list[dict[str, Any]] | None = None,
) -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {"id": person_id, "names": [{"value": "Test User", "usage": "professional"}]},
        "experiences": experiences or [],
        "skills": [],
        "education": [],
        "organizations": _collect_orgs(experiences),
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
) -> dict:
    dr: dict[str, Any] = {}
    if start is not None:
        dr["start"] = start
    if end is not None:
        dr["end"] = end
    dr["isCurrent"] = is_current
    return {
        "id": eid,
        "title": title,
        "organizationRefs": [{"id": org_id, "name": org_name, "type": "organization"}],
        "dateRange": dr,
    }


def _run_rule(rule, experiences: list[dict], **params) -> list[ReasoningResult]:
    profile = _profile(experiences=experiences)
    graph = KnowledgeGraphBuilder().build(profile)
    context = RuleContext(graph=graph, profile=profile, parameters=params)
    return rule.execute(context)


# ===================================================================
# date_utils unit tests
# ===================================================================


def test_parse_date_full_month() -> None:
    d = parse_date("2022-03")
    assert d is not None
    assert d.year == 2022
    assert d.month == 3


def test_parse_date_year_only() -> None:
    d = parse_date("2020")
    assert d is not None
    assert d.year == 2020
    assert d.month == 1


def test_parse_date_present_returns_none() -> None:
    assert parse_date("present") is None
    assert parse_date("now") is None
    assert parse_date("current") is None


def test_parse_date_none() -> None:
    assert parse_date(None) is None
    assert parse_date("") is None


def test_parse_date_range_full() -> None:
    dr = parse_date_range({"start": "2020-01", "end": "2023-06", "isCurrent": False})
    assert dr.start is not None
    assert dr.start.year == 2020
    assert dr.end is not None
    assert dr.end.year == 2023
    assert not dr.is_current


def test_parse_date_range_current() -> None:
    dr = parse_date_range({"start": "2020-01", "isCurrent": True})
    assert dr.start is not None
    assert dr.end is None
    assert dr.is_current


def test_parse_date_range_none() -> None:
    dr = parse_date_range(None)
    assert dr.start is None
    assert dr.end is None
    assert not dr.is_current


def test_duration_years_known() -> None:
    dr = parse_date_range({"start": "2020-01", "end": "2023-01", "isCurrent": False})
    y = duration_years(dr)
    assert abs(y - 3.0) < 0.02


def test_duration_years_current() -> None:
    dr = parse_date_range({"start": "2020-01", "isCurrent": True})
    y = duration_years(dr)
    assert y > 0


def test_duration_years_no_start() -> None:
    dr = parse_date_range({"end": "2023-01"})
    assert duration_years(dr) == 0.0


def test_merge_overlapping_periods_no_overlap() -> None:
    periods = [
        parse_date_range({"start": "2020-01", "end": "2021-01"}),
        parse_date_range({"start": "2022-01", "end": "2023-01"}),
    ]
    merged = merge_overlapping_periods(periods)
    assert len(merged) == 2


def test_merge_overlapping_periods_with_overlap() -> None:
    periods = [
        parse_date_range({"start": "2020-01", "end": "2022-06"}),
        parse_date_range({"start": "2022-01", "end": "2023-01"}),
    ]
    merged = merge_overlapping_periods(periods)
    assert len(merged) == 1
    assert merged[0].start is not None
    assert merged[0].start.year == 2020
    assert merged[0].end is not None
    assert merged[0].end.year == 2023


def test_merge_overlapping_periods_contained() -> None:
    periods = [
        parse_date_range({"start": "2020-01", "end": "2024-01"}),
        parse_date_range({"start": "2021-06", "end": "2022-06"}),
    ]
    merged = merge_overlapping_periods(periods)
    assert len(merged) == 1
    assert merged[0].start is not None
    assert merged[0].start.year == 2020
    assert merged[0].end is not None
    assert merged[0].end.year == 2024


def test_merge_overlapping_periods_current() -> None:
    periods = [
        parse_date_range({"start": "2020-01", "end": "2022-01"}),
        parse_date_range({"start": "2021-06", "isCurrent": True}),
    ]
    merged = merge_overlapping_periods(periods)
    assert len(merged) == 1
    assert merged[0].is_current


def test_merge_overlapping_periods_empty() -> None:
    assert merge_overlapping_periods([]) == []


def test_total_experience_years_simple() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Role B", "Org2", "org-2", "2022-01", "2023-01"),
    ]
    y = total_experience_years(exps)
    assert abs(y - 2.0) < 0.1


def test_total_experience_years_with_overlap() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2022-06"),
        _exp("e2", "Role B", "Org1", "org-1", "2022-01", "2023-01"),
    ]
    y = total_experience_years(exps)
    assert abs(y - 3.0) < 0.1


def test_total_experience_years_empty() -> None:
    assert total_experience_years([]) == 0.0


def test_format_duration_years_only() -> None:
    assert format_duration(3.0) == "3 years"


def test_format_duration_years_and_months() -> None:
    assert format_duration(3.5) == "3 years 6 months"


def test_format_duration_months_only() -> None:
    assert format_duration(0.5) == "6 months"


def test_format_duration_zero() -> None:
    assert format_duration(0) == "0 months"


def test_title_level_default() -> None:
    assert title_level("Engineer") == 2


def test_title_level_junior() -> None:
    assert title_level("Junior Engineer") == 1


def test_title_level_senior() -> None:
    assert title_level("Senior Engineer") == 3


def test_title_level_director() -> None:
    assert title_level("Director of Engineering") == 4


def test_title_level_chief() -> None:
    assert title_level("Chief Technology Officer") == 5


def test_title_level_case_insensitive() -> None:
    assert title_level("senior manager") == 3


def test_employment_gaps_no_gaps() -> None:
    exps = [
        _exp("e1", "Role A", "O1", "o1", "2020-01", "2021-01-15"),
        _exp("e2", "Role B", "O2", "o2", "2021-01-20", "2022-01"),
    ]
    gaps = employment_gaps(exps, min_gap_days=30)
    assert gaps == []


def test_employment_gaps_with_gap() -> None:
    exps = [
        _exp("e1", "Role A", "O1", "o1", "2020-01", "2021-01"),
        _exp("e2", "Role B", "O2", "o2", "2022-01", "2023-01"),
    ]
    gaps = employment_gaps(exps, min_gap_days=30)
    assert len(gaps) == 1
    assert gaps[0]["duration_days"] > 300


def test_employment_gaps_empty() -> None:
    assert employment_gaps([]) == []


def test_employment_gaps_below_threshold() -> None:
    exps = [
        _exp("e1", "Role A", "O1", "o1", "2020-01", "2020-02"),
        _exp("e2", "Role B", "O2", "o2", "2020-02-15", "2020-03"),
    ]
    gaps = employment_gaps(exps, min_gap_days=30)
    assert gaps == []


# ===================================================================
# TotalYearsExperienceRule
# ===================================================================


def test_total_years_no_experiences() -> None:
    results = _run_rule(TotalYearsExperienceRule(), [])
    assert len(results) == 1
    assert results[0].value == 0.0


def test_total_years_single_experience() -> None:
    exps = [_exp("e1", "Role", "Org", "org-1", "2020-01", "2023-01")]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert len(results) == 1
    assert abs(results[0].value - 3.0) < 0.1


def test_total_years_current_detected() -> None:
    exps = [_exp("e1", "Role", "Org", "org-1", "2020-01", is_current=True)]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert len(results) == 1
    assert results[0].value > 5.0
    assert results[0].metadata["has_current_employment"]


def test_total_years_overlapping() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2022-06"),
        _exp("e2", "Role B", "Org1", "org-1", "2022-01", "2023-01"),
    ]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert abs(results[0].value - 3.0) < 0.1


def test_total_years_metadata() -> None:
    exps = [
        _exp("e1", "Role", "Org", "org-1", "2020-01", "2021-01"),
    ]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    m = results[0].metadata
    assert m["experience_count"] == 1
    assert m["periods_after_merge"] == 1
    assert "formatted" in m
    assert m["formatted"] == "1 year"


# ===================================================================
# CurrentEmployerRule
# ===================================================================


def test_current_employer_found() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-acme", "2020-01", is_current=True),
    ]
    results = _run_rule(CurrentEmployerRule(), exps)
    assert len(results) == 1
    assert results[0].value == "Acme Corp"
    assert results[0].metadata["has_current"]


def test_current_employer_none() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-acme", "2020-01", "2021-01"),
    ]
    results = _run_rule(CurrentEmployerRule(), exps)
    assert results[0].value == "none"
    assert not results[0].metadata["has_current"]


def test_current_employer_empty() -> None:
    results = _run_rule(CurrentEmployerRule(), [])
    assert results[0].value == "none"


def test_current_employer_detects_latest() -> None:
    exps = [
        _exp("e1", "Old Role", "Old Corp", "org-old", "2018-01", "2020-01"),
        _exp("e2", "New Role", "New Corp", "org-new", "2020-06", is_current=True),
    ]
    results = _run_rule(CurrentEmployerRule(), exps)
    assert results[0].value == "New Corp"


# ===================================================================
# CurrentRoleRule
# ===================================================================


def test_current_role_found() -> None:
    exps = [
        _exp("e1", "Senior Engineer", "Acme Corp", "org-acme", "2020-01", is_current=True),
    ]
    results = _run_rule(CurrentRoleRule(), exps)
    assert results[0].value == "Senior Engineer"


def test_current_role_none() -> None:
    exps = [
        _exp("e1", "Old Role", "Acme Corp", "org-acme", "2020-01", "2021-01"),
    ]
    results = _run_rule(CurrentRoleRule(), exps)
    assert results[0].value == "none"


def test_current_role_empty() -> None:
    results = _run_rule(CurrentRoleRule(), [])
    assert results[0].value == "none"


# ===================================================================
# LongestTenureRule
# ===================================================================


def test_longest_tenure_found() -> None:
    exps = [
        _exp("e1", "Short", "Corp A", "org-a", "2021-01", "2022-01"),
        _exp("e2", "Long", "Corp B", "org-b", "2018-01", "2023-01"),
    ]
    results = _run_rule(LongestTenureRule(), exps)
    v = results[0].value
    assert v["employer"] == "Corp B"
    assert v["role"] == "Long"
    assert abs(v["duration_years"] - 5.0) < 0.1


def test_longest_tenure_empty() -> None:
    results = _run_rule(LongestTenureRule(), [])
    assert results[0].value == "none"


def test_longest_tenure_single() -> None:
    exps = [
        _exp("e1", "Solo", "My Corp", "org-my", "2020-01", "2023-01"),
    ]
    results = _run_rule(LongestTenureRule(), exps)
    v = results[0].value
    assert v["employer"] == "My Corp"
    assert v["role"] == "Solo"


# ===================================================================
# CareerProgressionRule
# ===================================================================


def test_career_progression_empty() -> None:
    results = _run_rule(CareerProgressionRule(), [])
    v = results[0].value
    assert v["events"] == []
    assert v["summary"]["total_roles"] == 0


def test_career_progression_single_role() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-acme", "2020-01", "2023-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    v = results[0].value
    assert len(v["events"]) == 2  # start + end
    assert v["summary"]["pattern"] == "single_role"


def test_career_progression_promotion_detected() -> None:
    exps = [
        _exp("e1", "Junior Engineer", "Acme Corp", "org-acme", "2018-01", "2020-01"),
        _exp("e2", "Senior Engineer", "Acme Corp", "org-acme", "2020-01", "2023-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    v = results[0].value
    assert v["summary"]["promotions"] == 1
    assert v["summary"]["pattern"] == "upward"


def test_career_progression_org_change_detected() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-acme", "2018-01", "2020-01"),
        _exp("e2", "Engineer", "Beta Inc", "org-beta", "2021-01", "2023-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    v = results[0].value
    assert v["summary"]["org_changes"] == 1
    assert v["summary"]["pattern"] == "lateral"


def test_career_progression_varied() -> None:
    exps = [
        _exp("e1", "Junior Engineer", "Acme Corp", "org-acme", "2018-01", "2020-01"),
        _exp("e2", "Senior Engineer", "Acme Corp", "org-acme", "2020-01", "2022-01"),
        _exp("e3", "Engineer", "Beta Inc", "org-beta", "2022-06", "2023-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    v = results[0].value
    assert v["summary"]["promotions"] >= 1
    assert v["summary"]["org_changes"] >= 1
    assert v["summary"]["pattern"] == "varied"


def test_career_progression_metadata() -> None:
    exps = [
        _exp("e1", "Role", "Acme Corp", "org-acme", "2020-01", "2021-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    assert results[0].metadata["total_events"] == 2
    assert results[0].metadata["promotions"] == 0
    assert results[0].metadata["org_changes"] == 0


# ===================================================================
# EmploymentGapRule
# ===================================================================


def test_employment_gap_no_gaps() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2021-01-15"),
        _exp("e2", "Role B", "Org2", "org-2", "2021-01-20", "2022-01"),
    ]
    results = _run_rule(EmploymentGapRule(), exps)
    assert results[0].value == []


def test_employment_gap_detected() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Role B", "Org2", "org-2", "2022-06", "2023-01"),
    ]
    results = _run_rule(EmploymentGapRule(), exps)
    assert len(results[0].value) == 1
    assert results[0].value[0]["duration_days"] > 400


def test_employment_gap_empty() -> None:
    results = _run_rule(EmploymentGapRule(), [])
    assert results[0].value == []


def test_employment_gap_threshold_parameter() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01", "2021-01"),
        _exp("e2", "Role B", "Org2", "org-2", "2021-02", "2022-01"),
    ]
    results = _run_rule(EmploymentGapRule(), exps, **{"employment_gap_min_days": 365})
    # Gap is ~31 days, threshold is 365 → no gaps
    assert results[0].value == []


# ===================================================================
# CareerStageRule
# ===================================================================


def test_career_stage_early() -> None:
    exps = [
        _exp("e1", "Engineer", "Org", "org-1", "2021-01", "2022-01"),
    ]
    results = _run_rule(CareerStageRule(), exps)
    assert results[0].value == "Early Career"


def test_career_stage_mid() -> None:
    exps = [
        _exp("e1", "Engineer", "Org", "org-1", "2020-01", "2024-01"),
    ]
    results = _run_rule(CareerStageRule(), exps)
    assert results[0].value == "Mid Career"


def test_career_stage_senior() -> None:
    exps = [
        _exp("e1", "Engineer", "Org", "org-1", "2016-01", "2024-01"),
    ]
    results = _run_rule(CareerStageRule(), exps)
    assert results[0].value == "Senior"


def test_career_stage_principal() -> None:
    exps = [
        _exp("e1", "Engineer", "Org", "org-1", "2012-01", "2024-01"),
    ]
    results = _run_rule(CareerStageRule(), exps)
    assert results[0].value == "Principal"


def test_career_stage_executive() -> None:
    exps = [
        _exp("e1", "Engineer", "Org", "org-1", "2008-01", "2024-01"),
    ]
    results = _run_rule(CareerStageRule(), exps)
    assert results[0].value == "Executive"


def test_career_stage_empty() -> None:
    results = _run_rule(CareerStageRule(), [])
    assert results[0].value == "Early Career"


# ===================================================================
# Integration: all tenure rules together
# ===================================================================


def test_all_tenure_rules_together() -> None:
    from careeros.reasoning import ReasoningEngine as RE
    from careeros.reasoning import RuleRegistry

    exps = [
        _exp("e1", "Junior Engineer", "Acme Corp", "org-acme", "2018-01", "2020-01"),
        _exp("e2", "Senior Engineer", "Acme Corp", "org-acme", "2020-01", "2024-06"),
        _exp("e3", "Lead Engineer", "Beta Inc", "org-beta", "2024-09", is_current=True),
    ]

    profile = _profile(experiences=exps)
    graph = KnowledgeGraphBuilder().build(profile)

    registry = RuleRegistry()
    registry.register(TotalYearsExperienceRule())
    registry.register(CurrentEmployerRule())
    registry.register(CurrentRoleRule())
    registry.register(LongestTenureRule())
    registry.register(CareerProgressionRule())
    registry.register(EmploymentGapRule())
    registry.register(CareerStageRule())

    engine = RE(registry)
    analysis = engine.run(graph, profile=profile)

    findings = {r.finding_type: r for r in analysis.reasoning_results}
    assert findings["total_years_of_experience"].value >= 5.0
    assert findings["current_employer"].value == "Beta Inc"
    assert findings["current_role"].value == "Lead Engineer"
    assert findings["longest_tenure"].value["employer"] == "Acme Corp"
    assert findings["career_progression_timeline"].value["summary"]["promotions"] >= 1
    assert findings["career_stage_classification"].value == "Senior"

    assert analysis.execution_stats["total_rules"] == 7
    assert analysis.execution_stats["total_findings"] == 7


def test_all_tenure_rules_deterministic() -> None:
    from careeros.reasoning import ReasoningEngine as RE
    from careeros.reasoning import RuleRegistry

    exps = [
        _exp("e1", "Role", "Org", "org-1", "2020-01", "2021-01"),
    ]
    profile = _profile(experiences=exps)
    graph = KnowledgeGraphBuilder().build(profile)

    registry = RuleRegistry()
    registry.register(TotalYearsExperienceRule())
    registry.register(CurrentEmployerRule())
    registry.register(CurrentRoleRule())

    engine = RE(registry)
    a1 = engine.run(graph, profile=profile)
    a2 = engine.run(graph, profile=profile)
    assert a1.reasoning_results == a2.reasoning_results


# ===================================================================
# Edge cases
# ===================================================================


def test_single_day_experience() -> None:
    exps = [
        _exp("e1", "Freelance", "Client", "org-client", "2023-06-01", "2023-06-01"),
    ]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert results[0].value < 0.1


def test_concurrent_same_org_not_double_counted() -> None:
    exps = [
        _exp("e1", "FT Role", "Acme Corp", "org-acme", "2020-01", "2023-01"),
        _exp("e2", "PT Role", "Acme Corp", "org-acme", "2021-01", "2022-06"),
    ]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert abs(results[0].value - 3.0) < 0.1


def test_no_organization_ref() -> None:
    exps = [
        {
            "id": "e1",
            "title": "Freelancer",
            "dateRange": {"start": "2020-01", "end": "2021-01"},
        }
    ]
    results = _run_rule(CurrentEmployerRule(), exps)
    assert results[0].value == "none"


def test_title_not_set() -> None:
    exps = [
        _exp("e1", "", "Org", "org-1", "2020-01", "2021-01"),
    ]
    results = _run_rule(CurrentRoleRule(), exps)
    assert results[0].value == "none"


def test_missing_date_range_does_not_crash() -> None:
    exps = [
        {"id": "e1", "title": "Role", "organizationRefs": [{"id": "org-1", "name": "Org"}]},
    ]
    results = _run_rule(TotalYearsExperienceRule(), exps)
    assert results[0].value == 0.0


def test_gap_threshold_ignores_small_gaps() -> None:
    exps = [
        _exp("e1", "Role A", "Org1", "org-1", "2020-01-01", "2020-06-01"),
        _exp("e2", "Role B", "Org2", "org-2", "2020-06-15", "2021-01-01"),
    ]
    # Gap is 14 days, threshold is 30 → no gaps reported
    results = _run_rule(EmploymentGapRule(), exps, **{"employment_gap_min_days": 30})
    assert results[0].value == []


def test_org_name_and_id_no_refs() -> None:
    from careeros.reasoning.rules.tenure_rules import _org_name_and_id

    exp = {"id": "e1", "title": "Role"}
    context = RuleContext(
        graph=KnowledgeGraphBuilder().build(_profile()),
        profile=_profile(),
    )
    name, oid = _org_name_and_id(exp, context)
    assert name == "Unknown Organization"
    assert oid is None


# ===================================================================
# Confidence is always 1.0 for deterministic rules
# ===================================================================


def test_all_rules_have_confidence_one() -> None:
    exps = [
        _exp("e1", "Role", "Org", "org-1", "2020-01", "2021-01"),
    ]
    for rule_cls in [
        TotalYearsExperienceRule,
        CurrentEmployerRule,
        CurrentRoleRule,
        LongestTenureRule,
        CareerProgressionRule,
        EmploymentGapRule,
        CareerStageRule,
    ]:
        results = _run_rule(rule_cls(), exps)
        for r in results:
            assert r.confidence == 1.0, f"{rule_cls.__name__} result confidence should be 1.0"


def test_total_years_finding_type() -> None:
    results = _run_rule(TotalYearsExperienceRule(), [])
    assert results[0].finding_type == "total_years_of_experience"


def test_current_employer_finding_type() -> None:
    results = _run_rule(CurrentEmployerRule(), [])
    assert results[0].finding_type == "current_employer"


def test_longest_tenure_formatted_duration() -> None:
    exps = [
        _exp("e1", "Long Role", "Org", "org-1", "2020-01", "2023-06"),
    ]
    results = _run_rule(LongestTenureRule(), exps)
    v = results[0].value
    assert isinstance(v, dict)
    assert "formatted_duration" in v
    assert v["formatted_duration"] != ""


def test_career_progression_events_have_all_fields() -> None:
    exps = [
        _exp("e1", "Engineer", "Acme Corp", "org-acme", "2020-01", "2021-01"),
    ]
    results = _run_rule(CareerProgressionRule(), exps)
    for event in results[0].value["events"]:
        assert "date" in event
        assert "type" in event
        assert "title" in event
        assert "organization" in event
        assert "experience_id" in event
