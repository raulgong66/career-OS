"""Unified deterministic recommendation model (ADR-009).

M1.24.1 normalizes ``ProfileQualityReport`` findings into a single
deterministic recommendation shape shared across workspaces. The
optimization-source mapping is implemented as a duck-typed merge so the
Profile Quality Engine never depends on ``careeros.optimizer`` (ADR-009: the
engines are complementary and stay decoupled); the Resume Workspace / Tailoring
supply an ``OptimizationResult`` when a Job Description is provided (M1.24.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .report import ProfileQualityReport

SOURCE_PROFILE_QUALITY = "profile_quality"
SOURCE_OPTIMIZATION = "optimization"

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


@dataclass(frozen=True)
class UnifiedRecommendation:
    """Normalized recommendation from any source (ADR-009 SS'Unified shape')."""

    id: str
    source: str
    rule_id: str
    element_id: str
    element_type: str
    title: str
    reason: str
    suggested_action: str
    resolution_type: str
    evidence_refs: list[str]
    priority: str
    estimated_impact: str
    confidence: str
    jd_match_score: float | None = None
    context_match_score: float | None = None
    weighted_total: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "rule_id": self.rule_id,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "title": self.title,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "resolution_type": self.resolution_type,
            "evidence_refs": list(self.evidence_refs),
            "priority": self.priority,
            "estimated_impact": self.estimated_impact,
            "confidence": self.confidence,
            "jd_match_score": self.jd_match_score,
            "context_match_score": self.context_match_score,
            "weighted_total": self.weighted_total,
        }


def unified_recommendation_sort_key(recommendation: UnifiedRecommendation) -> tuple:
    """Deterministic queue ordering: priority, impact, then stable tie-breakers."""
    return (
        -_PRIORITY_RANK.get(recommendation.priority, 0),
        -_PRIORITY_RANK.get(recommendation.estimated_impact, 0),
        recommendation.rule_id,
        recommendation.element_id,
        recommendation.id,
    )


def to_unified_recommendations(
    profile_quality_report: ProfileQualityReport,
    optimization_result: Any | None = None,
) -> list[UnifiedRecommendation]:
    """Normalize both sources into a single list.

    Deduplication key is ``(rule_id, element_id)``; when both sources produce
    the same key, ``profile_quality`` wins because the structural fix it
    represents enables the optimization (ADR-009 deduplication policy).
    """
    items: list[UnifiedRecommendation] = [
        UnifiedRecommendation(
            id=f"{finding.rule_id}:{finding.element_id}",
            source=SOURCE_PROFILE_QUALITY,
            rule_id=finding.rule_id,
            element_id=finding.element_id,
            element_type=finding.element_type,
            title=finding.title,
            reason=finding.reason,
            suggested_action=finding.suggested_action,
            resolution_type=finding.resolution_type,
            evidence_refs=list(finding.evidence_refs),
            priority=finding.priority,
            estimated_impact=finding.estimated_impact,
            confidence=finding.confidence,
        )
        for finding in profile_quality_report.findings
    ]

    if optimization_result is not None:
        items.extend(_from_optimization_result(optimization_result))

    return _dedupe(items)


def filter_and_sort_recommendations(
    recommendations: list[UnifiedRecommendation],
    *,
    priority: str | None = None,
    resolution_type: str | None = None,
) -> list[UnifiedRecommendation]:
    """Filter by priority/resolution type and order deterministically."""
    filtered = list(recommendations)
    if priority:
        filtered = [r for r in filtered if r.priority == priority]
    if resolution_type:
        filtered = [r for r in filtered if r.resolution_type == resolution_type]
    return sorted(filtered, key=unified_recommendation_sort_key)


def _from_optimization_result(result: Any) -> list[UnifiedRecommendation]:
    """Map ``OptimizationResult.Recommendation`` items (duck-typed).

    ``result`` is expected to expose ``recommendations``; each item exposes
    ``id``, ``type``, ``display_name``, ``details``, ``evidence``, and
    ``scores`` (see ``careeros.optimizer.Recommendation``). No optimizer import
    happens here so the engines stay decoupled.
    """
    items: list[UnifiedRecommendation] = []
    for rec in getattr(result, "recommendations", []) or []:
        scores = getattr(rec, "scores", None) or {}
        rec_type = str(getattr(rec, "type", "") or "")
        element_id = str(getattr(rec, "id", "") or "") or rec_type
        evidence = getattr(rec, "evidence", None) or []
        items.append(
            UnifiedRecommendation(
                id=f"optimization:{element_id}",
                source=SOURCE_OPTIMIZATION,
                rule_id=rec_type,
                element_id=element_id,
                element_type=rec_type,
                title=str(getattr(rec, "display_name", "") or "") or rec_type,
                reason=str(getattr(rec, "details", "") or ""),
                suggested_action="Add evidence-backed content to the artifact.",
                resolution_type="none",
                evidence_refs=[
                    str(ev.get("id", "")) for ev in evidence if isinstance(ev, dict) and ev.get("id")
                ],
                priority="medium",
                estimated_impact="medium",
                confidence="medium",
                jd_match_score=_as_optional_float(scores.get("job_description_match")),
                context_match_score=_as_optional_float(scores.get("target_context_match")),
                weighted_total=_as_optional_float(scores.get("weighted_total")),
            )
        )
    return items


def _as_optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _dedupe(items: list[UnifiedRecommendation]) -> list[UnifiedRecommendation]:
    """Deduplicate by ``(rule_id, element_id)`` keeping the first occurrence.

    Profile-quality items are added first, so they win on conflict by policy.
    """
    seen: set[tuple[str, str]] = set()
    out: list[UnifiedRecommendation] = []
    for item in items:
        key = (item.rule_id, item.element_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


__all__ = [
    "SOURCE_OPTIMIZATION",
    "SOURCE_PROFILE_QUALITY",
    "UnifiedRecommendation",
    "filter_and_sort_recommendations",
    "to_unified_recommendations",
    "unified_recommendation_sort_key",
]
