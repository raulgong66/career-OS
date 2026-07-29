from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ReasoningReport


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
