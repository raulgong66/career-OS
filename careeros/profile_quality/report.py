"""Profile quality report models (M1.24.1).

Deterministic, evidence-traceable structures produced by the Profile Quality
Engine. These are Core data types (ADR-004): they carry no delivery, UI,
artifact, or job-description concepts (ADR-009).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from careeros.resolution import RESOLVABLE_RULES

PROFILE_QUALITY_ENGINE_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Rule -> dimension mapping (M1.24 Spec SS3.4 / Discovery SS6.2, AC 1.4)
# ---------------------------------------------------------------------------

RULE_ID_TO_DIMENSION: dict[str, str] = {
    "recommendation_add_measurable_achievement": "achievement_measurability",
    "recommendation_show_skill_in_experience": "skill_evidence_coverage",
    "recommendation_add_technologies": "technology_presence",
    "recommendation_improve_summary": "summary_quality",
    "recommendation_remove_duplicate_skills": "skill_deduplication",
    "recommendation_add_business_outcome": "business_outcome_language",
    "recommendation_show_certification_value": "certification_utilization",
    "recommendation_add_skills_to_project": "project_skill_linkage",
}

# Resolution Engine's RESOLVABLE_RULES holds rule class names; map them to
# rule ids so the resolvable set stays derived from the single source of truth
# (careeros.resolution) instead of being duplicated here.
RESOLVABLE_CLASS_TO_RULE_ID: dict[str, str] = {
    "ProjectWithoutSkillsRule": "recommendation_add_skills_to_project",
    "ExperienceNoTechnologiesRule": "recommendation_add_technologies",
    "SkillWithoutExperienceRule": "recommendation_show_skill_in_experience",
    "NoMeasurableAchievementRule": "recommendation_add_measurable_achievement",
}

AUTO_RESOLVABLE_RULE_IDS: frozenset[str] = frozenset(
    RESOLVABLE_CLASS_TO_RULE_ID[rule_class]
    for rule_class in RESOLVABLE_RULES
    if rule_class in RESOLVABLE_CLASS_TO_RULE_ID
)

_PROFILE_ELEMENT = "profile"


def resolution_type_for_rule(rule_id: str) -> str:
    """Return the resolution type for a profile-quality rule id.

    ``"auto"`` for the four rules the Resolution Engine can fix, ``"guided"``
    otherwise (ADR-009 source mapping table).
    """
    return "auto" if rule_id in AUTO_RESOLVABLE_RULE_IDS else "guided"


@dataclass(frozen=True)
class Citation:
    """Evidence citation for a finding (M1.24 Spec SS3.5, AC 1.3)."""

    entity_id: str
    entity_type: str
    property_path: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "property_path": self.property_path,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class Finding:
    """Single profile-quality finding (M1.24 Spec SS3.5).

    Each finding is tagged with its health dimension, carries a deterministic
    resolution type, and cites the canonical element it refers to.
    """

    rule_id: str
    dimension: str
    element_id: str
    element_type: str
    title: str
    reason: str
    suggested_action: str
    resolution_type: str
    evidence_refs: tuple[str, ...] = ()
    priority: str = "medium"
    estimated_impact: str = "medium"
    confidence: str = "medium"
    citations: tuple[Citation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "dimension": self.dimension,
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
            "citations": [c.to_dict() for c in self.citations],
        }


@dataclass(frozen=True)
class DimensionScore:
    """Score for one health dimension (M1.24 Spec SS3.5)."""

    name: str
    score: float
    weight: float
    findings: tuple[Finding, ...] = ()
    citations: tuple[Citation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "findings": [f.to_dict() for f in self.findings],
            "citations": [c.to_dict() for c in self.citations],
        }


@dataclass(frozen=True)
class HealthDimension:
    """Descriptor for one deterministic health dimension."""

    name: str
    weight: float
    label: str
    description: str


@dataclass(frozen=True)
class ProfileQualityReport:
    """Complete profile quality analysis report (M1.24 Spec SS3.5).

    All fields except ``generated_at`` are derived deterministically from the
    canonical profile dict.
    """

    profile_id: str
    profile_version: str
    health_score: int
    dimension_scores: tuple[DimensionScore, ...]
    findings: tuple[Finding, ...]
    citations: tuple[Citation, ...]
    generated_at: datetime
    engine_version: str = PROFILE_QUALITY_ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "health_score": self.health_score,
            "dimension_scores": [d.to_dict() for d in self.dimension_scores],
            "findings": [f.to_dict() for f in self.findings],
            "citations": [c.to_dict() for c in self.citations],
            "generated_at": self.generated_at.isoformat(),
            "engine_version": self.engine_version,
        }


__all__ = [
    "AUTO_RESOLVABLE_RULE_IDS",
    "Citation",
    "DimensionScore",
    "Finding",
    "HealthDimension",
    "PROFILE_QUALITY_ENGINE_VERSION",
    "ProfileQualityReport",
    "RESOLVABLE_CLASS_TO_RULE_ID",
    "RULE_ID_TO_DIMENSION",
    "resolution_type_for_rule",
]
