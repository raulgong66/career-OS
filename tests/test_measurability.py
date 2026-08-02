"""M1.17 — Public Measurability API tests.

Covers the public ``is_measurable`` Core API, the existing dict-based
``_is_measurable`` backward-compatibility layer in the reasoning rules file,
and regression against current behavior (resolution engine, existing test
suite).
"""

from __future__ import annotations

import pytest

from careeros import is_measurable
from careeros.measurability import is_measurable as core_is_measurable


# --------------------------------------------------------------------------
# Public API tests
# --------------------------------------------------------------------------


def test_measurable_with_digit_percentage() -> None:
    assert core_is_measurable("Reduced deployment time by 60%") is True


def test_measurable_with_count() -> None:
    assert core_is_measurable("Migrated 240 servers to AWS") is True


def test_measurable_with_currency() -> None:
    assert core_is_measurable("Saved $500k annually through automation") is True


def test_measurable_with_business_outcome_verb() -> None:
    assert core_is_measurable("Reduced infrastructure costs through migration") is True


def test_measurable_with_multiple_keywords() -> None:
    assert core_is_measurable("Delivered 30% revenue growth in Q3") is True


def test_non_measurable_generic_statement() -> None:
    assert core_is_measurable("Responsible for team coordination") is False


def test_non_measurable_vague_work() -> None:
    assert core_is_measurable("Worked on various projects") is False


def test_non_measurable_short_statement() -> None:
    assert core_is_measurable("Helped with tasks") is False


def test_non_measurable_purely_qualitative() -> None:
    assert core_is_measurable("Collaborated effectively with cross-functional teams") is False


def test_empty_string() -> None:
    assert core_is_measurable("") is False


def test_whitespace_only() -> None:
    assert core_is_measurable("   ") is False


def test_none_implies_false() -> None:
    assert core_is_measurable(None) is False  # type: ignore[arg-type]


def test_measurable_uptime_keyword() -> None:
    assert core_is_measurable("Improved system uptime to 99.99%") is True


def test_measurable_scaling_keyword() -> None:
    assert core_is_measurable("Scaled the platform to handle 1M requests") is True


def test_measurable_cost_keyword_without_digit() -> None:
    assert core_is_measurable("Reduced costs through infrastructure optimization") is True


def test_non_measurable_without_outcome_word_or_digit() -> None:
    assert core_is_measurable("Led a team of engineers") is False


def test_measurable_with_multiple_lines() -> None:
    assert core_is_measurable("Designed and implemented CI/CD pipeline.\nReduced deployment time from 2h to 10m.") is True


def test_deterministic() -> None:
    text = "Reduced deployment time by 60%"
    results = [core_is_measurable(text) for _ in range(10)]
    assert all(r is True for r in results)


# --------------------------------------------------------------------------
# Public API name
# --------------------------------------------------------------------------


def test_exported_from_careeros_facade() -> None:
    assert is_measurable is core_is_measurable


# --------------------------------------------------------------------------
# Regression: resolution engine
# --------------------------------------------------------------------------


def test_resolution_engine_uses_core_api() -> None:
    """resolution.py no longer imports from private reasoning internals."""
    from careeros.resolution import apply_resolution

    assert apply_resolution is not None


def test_resolution_rejects_non_measurable_achievement() -> None:
    from careeros import AchievementNotMeasurableError
    from careeros.resolution import apply_resolution

    data = {
        "experiences": [{"id": "exp-1", "scope": "Led a team", "achievementRefs": []}],
        "achievements": [],
        "artifacts": [],
    }
    with pytest.raises(AchievementNotMeasurableError, match="does not look measurable"):
        apply_resolution(
            data,
            triggered_rule="NoMeasurableAchievementRule",
            element_id="exp-1",
            achievement_statement="Worked hard on things",
        )


def test_resolution_accepts_measurable_achievement() -> None:
    from careeros.resolution import apply_resolution

    data = {
        "experiences": [
            {"id": "exp-1", "scope": "Led a team", "achievementRefs": []}
        ],
        "achievements": [],
        "artifacts": [],
    }
    apply_resolution(
        data,
        triggered_rule="NoMeasurableAchievementRule",
        element_id="exp-1",
        achievement_statement="Reduced deployment time by 60% through CI/CD",
    )
    assert any(
        "60%" in a.get("statement", "")
        for a in data.get("achievements", [])
    )


# --------------------------------------------------------------------------
# Regression: existing recommendation rules still work
# --------------------------------------------------------------------------


def test_recommendation_rules_still_importable() -> None:
    """The private module still exists and loads without error."""
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable is not None


def test_recommendation_rules_wrapper_with_metrics() -> None:
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable({"metrics": ["cost reduction"]}) is True


def test_recommendation_rules_wrapper_with_statement() -> None:
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable({"statement": "Reduced deployment time by 60%"}) is True


def test_recommendation_rules_wrapper_non_measurable() -> None:
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable({"statement": "Worked on sundry tasks"}) is False


def test_recommendation_rules_wrapper_none() -> None:
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable(None) is False


def test_recommendation_rules_wrapper_empty() -> None:
    from careeros.reasoning.rules.recommendation_rules import _is_measurable

    assert _is_measurable({}) is False