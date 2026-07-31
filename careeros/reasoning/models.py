from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from careeros.knowledge import KnowledgeGraph


@dataclass(frozen=True)
class ReasoningResult:
    rule_id: str
    finding_type: str
    value: Any
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class Evidence:
    id: str
    type: str
    source: str
    summary: str
    references: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class ProfileRecommendation:
    """A deterministic, evidence-backed profile recommendation.

    Confidence, priority, and estimated impact are qualitative by design
    (ADR-003): ``"high"``, ``"medium"``, or ``"low"`` — no numeric scores are
    exposed to the frontend. New action-guidance fields carry a default so
    existing consumers keep working (backward compatibility).
    """

    id: str
    title: str
    reason: str
    element_id: str | None
    element_type: str | None
    confidence: str
    future_evidence: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)
    explanation: str = ""
    suggested_action: str = ""
    examples: tuple[str, ...] = ()
    priority: str = "medium"
    estimated_impact: str = "medium"
    detected_pattern: str = ""
    missing_information: tuple[str, ...] = ()
    recruiter_impact: str = ""
    triggered_rule: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "reason": self.reason,
            "explanation": self.explanation,
            "suggested_action": self.suggested_action,
            "examples": list(self.examples),
            "priority": self.priority,
            "estimated_impact": self.estimated_impact,
            "detected_pattern": self.detected_pattern,
            "missing_information": list(self.missing_information),
            "recruiter_impact": self.recruiter_impact,
            "triggered_rule": self.triggered_rule,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "confidence": self.confidence,
            "future_evidence": dict(self.future_evidence),
        }


@dataclass(frozen=True)
class EvidenceSet:
    theme: str
    evidence: tuple[Evidence, ...] = ()
    findings: tuple[ReasoningResult, ...] = ()


@dataclass(frozen=True)
class RuleContext:
    graph: KnowledgeGraph
    profile: dict[str, Any]
    parameters: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class AnalysisModel:
    profile_id: str
    generated_at: datetime
    reasoning_results: tuple[ReasoningResult, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    evidence_sets: tuple[EvidenceSet, ...] = ()
    execution_stats: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class EvidencePackage:
    meta: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)
    candidate_summary: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)
    relevant_experiences: tuple[dict[str, Any], ...] = ()
    matching_skills: tuple[dict[str, Any], ...] = ()
    education: tuple[dict[str, Any], ...] = ()
    strengths: tuple[dict[str, Any], ...] = ()
    weaknesses: tuple[dict[str, Any], ...] = ()
    missing_competencies: tuple[dict[str, Any], ...] = ()
    supporting_evidence: tuple[dict[str, Any], ...] = ()
    recommendations: tuple[dict[str, Any], ...] = ()
    rule_summary: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


def _finding_to_dict(f: ReasoningResult) -> dict[str, Any]:
    return {
        "rule_id": f.rule_id,
        "finding_type": f.finding_type,
        "value": f.value,
        "confidence": f.confidence,
        "evidence_refs": list(f.evidence_refs),
        "metadata": dict(f.metadata),
    }


REASONING_ENGINE_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReasoningReport:
    engine_version: str = REASONING_ENGINE_VERSION
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    profile_id: str = "unknown"
    findings: tuple[ReasoningResult, ...] = ()
    findings_by_type: dict[str, tuple[ReasoningResult, ...]] = field(default_factory=dict)
    recommendations: tuple[ProfileRecommendation, ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)
    execution_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "generated_at": self.generated_at.isoformat(),
            "profile_id": self.profile_id,
            "findings": [_finding_to_dict(f) for f in self.findings],
            "findings_by_type": {
                k: [_finding_to_dict(f) for f in v]
                for k, v in self.findings_by_type.items()
            },
            "recommendations": [r.to_dict() for r in self.recommendations],
            "summary": dict(self.summary),
            "execution_stats": dict(self.execution_stats),
        }

    def to_json(self, indent: int = 2) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, default=str)
