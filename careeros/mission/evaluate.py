"""Mission evaluation over the existing deterministic engine.

Evaluation is a thin, read-only orchestration over the optimizer and the
partner-facing rendering layer. It never re-scores, never recomputes
evidence strength, confidence, provenance, or coverage: every value in
:class:`MissionEvaluationResult` is derived from the optimizer's own
computation (``CVOptimizer.optimize_cv``) and the existing presentation
helpers (``careeros.reporting.partner_output``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from ..optimizer import CVOptimizer, EntityNotFoundError, Recommendation
from ..reporting import partner_output
from ..reporting.partner_output import (
    evidence_backed_concepts,
    evidence_backed_coverage,
    render_recommendation,
)
from .contract import MissionContract

logger = logging.getLogger(__name__)


class MissionStatus(str, Enum):
    """Deterministic mission status derived from engine coverage values."""

    NO_REQUIREMENTS = "no_requirements"
    EVIDENCE_GAPS = "evidence_gaps"
    PARTIAL_EVIDENCE = "partial_evidence"
    EVIDENCE_BACKED = "evidence_backed"


class RequirementStatus(str, Enum):
    """Per-requirement status derived from evidence-backed matches."""

    EVIDENCED = "evidenced"
    REFERENCED_WITHOUT_EVIDENCE = "referenced_without_evidence"
    GAP = "gap"


@dataclass(frozen=True)
class RequirementCoverage:
    """Coverage status of one mission requirement (all values engine-derived)."""

    requirement: str
    status: RequirementStatus
    evidence_backed: bool
    referenced: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement,
            "status": self.status.value,
            "evidence_backed": self.evidence_backed,
            "referenced": self.referenced,
        }


@dataclass
class MissionEvaluationResult:
    """Mission-framed evaluation result built only from existing engine data."""

    mission_id: str
    mission_statement: str
    role: str
    status: MissionStatus
    message: str
    text_coverage: float
    evidence_backed_coverage: float
    requirements: list[RequirementCoverage] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    candidate: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "mission_statement": self.mission_statement,
            "role": self.role,
            "status": self.status.value,
            "message": self.message,
            "text_coverage": self.text_coverage,
            "evidence_backed_coverage": self.evidence_backed_coverage,
            "requirements": [r.to_dict() for r in self.requirements],
            "recommendations": self.recommendations,
            "candidate": self.candidate,
        }


def _concept_names(concept_ids: Iterable[str]) -> set[str]:
    from ..optimizer import _CONCEPT_NAMES

    return {name for cid in concept_ids if (name := _CONCEPT_NAMES.get(cid))}


def _derive_mission_status(requirement_statuses: list[RequirementStatus]) -> MissionStatus:
    evidenced = sum(1 for status in requirement_statuses if status is RequirementStatus.EVIDENCED)
    referenced = sum(
        1
        for status in requirement_statuses
        if status is not RequirementStatus.EVIDENCED
    )
    if not requirement_statuses:
        return MissionStatus.NO_REQUIREMENTS
    if evidenced == len(requirement_statuses):
        return MissionStatus.EVIDENCE_BACKED
    if evidenced > 0 and referenced > 0:
        return MissionStatus.PARTIAL_EVIDENCE
    return MissionStatus.EVIDENCE_GAPS


_STATUS_MESSAGES: dict[MissionStatus, str] = {
    MissionStatus.NO_REQUIREMENTS: (
        "This mission has no requirements that match the candidate's profile."
    ),
    MissionStatus.EVIDENCE_GAPS: (
        "This candidate has not yet demonstrated any of this mission's requirements. "
        "Evidence gaps must be addressed before a recommendation can be issued."
    ),
    MissionStatus.PARTIAL_EVIDENCE: (
        "This candidate demonstrates some of the mission's requirements, but not all. "
        "The remaining evidence gaps must be addressed before a full recommendation can be issued."
    ),
    MissionStatus.EVIDENCE_BACKED: (
        "This candidate's profile demonstrates every requirement of the mission with "
        "evidence-backed records."
    ),
}


def _first_cv_artifact(profile: dict[str, Any]) -> str | None:
    for artifact in profile.get("artifacts") or []:
        artifact_type = (artifact.get("artifactType") or "").lower()
        if artifact_type in {"cv", "resume"} and artifact.get("id"):
            return artifact["id"]
    return None


def build_job_description(contract: MissionContract) -> str:
    """Deterministic job-description-style text derived from the contract.

    The optimizer extracts requirements from this text through its own
    pipeline, so contract requirements stay canonical and no new extraction
    path is introduced.
    """
    lines = [contract.role]
    lines.extend(contract.requirements)
    return "\n".join(line for line in lines if line)


def evaluate_mission(
    profile: dict[str, Any],
    contract: MissionContract,
    artifact_id: str | None = None,
) -> MissionEvaluationResult:
    """Evaluate a Mission Contract against a profile using existing machinery.

    Raises:
        EntityNotFoundError: When the target artifact is missing.
    """
    artifact = artifact_id or _first_cv_artifact(profile)
    if not artifact:
        raise EntityNotFoundError("Profile has no CV or resume artifact to evaluate.")

    optimizer = CVOptimizer(profile)
    job_description = build_job_description(contract)
    result = optimizer.optimize_cv(artifact, job_description=job_description)

    summary = result.summary
    jd_concepts = partner_output.jd_concepts_from_text(job_description)
    text_coverage = round(summary.requirement_coverage or 0.0, 1) if summary else 0.0
    ev_backed = round(evidence_backed_coverage(optimizer, jd_concepts), 1)

    ev_backed_concepts = evidence_backed_concepts(optimizer)
    matched_names = set(summary.matched_requirements) if summary else set()

    requirement_statuses: list[RequirementStatus] = []
    coverage_rows: list[RequirementCoverage] = []
    for requirement in contract.requirements:
        concepts = CVOptimizer._resolve_concepts([requirement])
        backed = bool(concepts & ev_backed_concepts)
        referenced = bool(_concept_names(concepts) & matched_names)
        status = (
            RequirementStatus.EVIDENCED
            if backed
            else RequirementStatus.REFERENCED_WITHOUT_EVIDENCE
            if referenced
            else RequirementStatus.GAP
        )
        requirement_statuses.append(status)
        coverage_rows.append(
            RequirementCoverage(
                requirement=requirement,
                status=status,
                evidence_backed=backed,
                referenced=referenced,
            )
        )

    mission_status = _derive_mission_status(requirement_statuses)
    names = (profile.get("person") or {}).get("names") or []
    candidate = names[0].get("value") if names else profile.get("id", "")

    return MissionEvaluationResult(
        mission_id=contract.mission_id,
        mission_statement=contract.mission_statement,
        role=contract.role,
        status=mission_status,
        message=_STATUS_MESSAGES[mission_status],
        text_coverage=text_coverage,
        evidence_backed_coverage=ev_backed,
        requirements=coverage_rows,
        recommendations=[rec.to_dict() for rec in result.recommendations or []],
        candidate=candidate,
    )


def evaluate_mission_many(
    profiles: Iterable[tuple[str, dict[str, Any]]],
    contract: MissionContract,
) -> list[dict[str, Any]]:
    """Evaluate a Mission Contract against several profiles.

    Thin orchestration only: each profile is evaluated through the existing
    :func:`evaluate_mission` with its own optimizer run, so every candidate
    keeps an independent evidence-backed result. Results preserve the input
    order and no new scoring, evidence, or confidence logic is introduced.
    """
    results: list[dict[str, Any]] = []
    for profile_id, profile in profiles:
        result = evaluate_mission(profile, contract)
        results.append({"profile_id": profile_id, "result": result.to_dict()})
    return results


def render_mission_result(result: MissionEvaluationResult) -> str:
    """Render a mission-framed partner-facing evaluation summary.

    Reuses the existing partner-facing labels and evidence rendering; no new
    scoring or provenance vocabulary is introduced.
    """
    lines = [f"### Mission: {result.mission_statement}", ""]
    lines.append(f"Primary role: {result.role}")
    lines.append(f"Mission status: {result.status.value}")
    lines.append(result.message)
    lines.append("")
    lines.append("Requirement coverage:")
    lines.append(f"  Text match:              {result.text_coverage:g}%")
    lines.append(f"  Evidence-backed:         {result.evidence_backed_coverage:g}%")
    for row in result.requirements:
        label = {
            RequirementStatus.EVIDENCED: "evidenced",
            RequirementStatus.REFERENCED_WITHOUT_EVIDENCE: "referenced, not evidenced",
            RequirementStatus.GAP: "evidence gap",
        }[row.status]
        lines.append(f"  - {row.requirement} ({label})")
    if any(
        row.status is RequirementStatus.REFERENCED_WITHOUT_EVIDENCE
        for row in result.requirements
    ):
        lines.append("")
        lines.append(partner_output._UNEVIDENCED_TEXT)
    lines.append("")
    lines.append("Evidence-backed recommendations:")
    if result.recommendations:
        for rec_dict in result.recommendations:
            rec = Recommendation(**rec_dict)
            lines.append("")
            lines.append(render_recommendation(rec))
    else:
        lines.append("  None.")
    lines.append("")
    lines.append("Human review required before this mission can be acted on.")
    return "\n".join(lines)
