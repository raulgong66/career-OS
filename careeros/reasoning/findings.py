from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ProfileRecommendation, ReasoningReport


@dataclass
class ReasoningFindings:
    """Deterministic reasoning findings extracted from a ReasoningReport.

    Exposes only what generators need — no internal engine details leaked.
    All fields are optional; consumers must handle None/empty gracefully.
    """

    strongest_skills: list[str] = field(default_factory=list)
    core_competencies: list[str] = field(default_factory=list)
    strongest_experience: dict[str, Any] | None = None
    leadership_indicators: list[dict[str, Any]] = field(default_factory=list)
    technology_breadth: list[str] = field(default_factory=list)
    domain_expertise: list[str] = field(default_factory=list)
    career_highlights: list[dict[str, Any]] = field(default_factory=list)
    career_stage: str | None = None

    @classmethod
    def from_report(cls, report: ReasoningReport) -> ReasoningFindings:
        findings = cls()
        for f in report.findings:
            ft = f.finding_type
            if ft == "strongest_skills":
                findings.strongest_skills = _extract_names(f.value)
            elif ft == "core_competencies":
                findings.core_competencies = _extract_names(f.value)
            elif ft == "strongest_experience":
                if isinstance(f.value, dict):
                    findings.strongest_experience = f.value
            elif ft == "leadership_experience":
                findings.leadership_indicators = _as_dict_list(f.value)
            elif ft == "technology_breadth":
                findings.technology_breadth = _extract_names(f.value)
            elif ft == "domain_experience":
                findings.domain_expertise = _extract_names(f.value)
            elif ft == "career_highlights":
                findings.career_highlights = _as_dict_list(f.value)
            elif ft == "career_stage_classification":
                if isinstance(f.value, str):
                    findings.career_stage = f.value
        return findings


def _extract_names(v: Any) -> list[str]:
    """Extract human-readable names from a finding value.

    Handles both plain lists of strings and lists of dicts with a 'name' key.
    """
    if isinstance(v, list):
        names: list[str] = []
        for item in v:
            if isinstance(item, dict):
                name = item.get("name") or item.get("label") or item.get("title", "")
                if name:
                    names.append(str(name))
            elif isinstance(item, str):
                names.append(item)
        return names
    if isinstance(v, str):
        return [v]
    return []


def _as_dict_list(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, list):
        return [item for item in v if isinstance(item, dict)]
    return []


VALID_CONFIDENCES = ("high", "medium", "low")
RECOMMENDATION_FINDING_PREFIX = "recommendation_"


@dataclass(frozen=True)
class ProfileRecommendations:
    """Deterministic profile recommendations extracted from a ReasoningReport.

    Recommendation rules emit findings whose ``finding_type`` starts with
    ``recommendation_``; this converter turns them into the public
    ``ProfileRecommendation`` shape consumed by the API and frontend.
    """

    items: tuple[ProfileRecommendation, ...] = ()

    @classmethod
    def from_report(cls, report: ReasoningReport) -> ProfileRecommendations:
        return cls.from_findings(report.findings)

    @classmethod
    def from_findings(cls, findings: Any) -> ProfileRecommendations:
        items: list[ProfileRecommendation] = []
        for f in findings:
            if not f.finding_type.startswith(RECOMMENDATION_FINDING_PREFIX):
                continue
            if not isinstance(f.value, dict):
                continue
            rec = _build_recommendation(f)
            if rec is not None:
                items.append(rec)
        return cls(items=tuple(items))

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


def _build_recommendation(f: Any) -> ProfileRecommendation | None:
    v = f.value
    title = v.get("title")
    reason = v.get("reason")
    if not title or not reason:
        return None

    element_id = v.get("element_id")
    element_type = v.get("element_type")
    raw_confidence = v.get("confidence", "medium")
    confidence = raw_confidence if raw_confidence in VALID_CONFIDENCES else "medium"

    future_evidence = v.get("future_evidence")
    if not isinstance(future_evidence, dict):
        future_evidence = {}

    return ProfileRecommendation(
        id=f"{f.finding_type}:{element_id or 'profile'}",
        title=str(title),
        reason=str(reason),
        element_id=element_id,
        element_type=element_type,
        confidence=str(confidence),
        future_evidence=future_evidence,
    )
