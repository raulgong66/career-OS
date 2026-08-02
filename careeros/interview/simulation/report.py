"""Interview Simulation — report builder (ADR-007, M1.18 refactor).

Deterministic assembly of the export-oriented ``InterviewReport`` and of a
completed session's ``InterviewSummary`` attachment. These live inside the
simulation module so the API layer stays a thin transport: it only invokes
this module and maps HTTP requests/responses.

The builder is stateless and deterministic: the same session and evaluation
summary always produce the same report.  No AI, no persistence, no scoring.
"""

from __future__ import annotations

from .domain import (
    EvaluationSummary,
    InterviewReport,
    InterviewSession,
    InterviewSummary,
    SessionMetrics,
)
from .engine import SessionEngine


def attach_summary(
    session: InterviewSession,
    summary: InterviewSummary,
) -> InterviewSession:
    """Return an immutable copy of ``session`` with ``summary`` attached.

    The session's ``summary`` field is populated from the computed
    ``InterviewSummary`` so later reads (e.g. ``GET`` / report) reflect the
    aggregate counts without mutating the original object.
    """
    return InterviewSession(
        id=session.id,
        plan_ref=session.plan_ref,
        profile_id=session.profile_id,
        state=session.state,
        questions=session.questions,
        answers=session.answers,
        started_at=session.started_at,
        completed_at=session.completed_at,
        paused_at=session.paused_at,
        metrics=session.metrics,
        summary=summary,
        metadata=session.metadata,
    )


def build_report(
    session: InterviewSession,
    evaluation_summary: EvaluationSummary,
) -> InterviewReport:
    """Build the export-oriented report for a completed session.

    Strengths / weaknesses / recommendations are advisory text derived
    deterministically from the qualitative evaluation counts (ADR-003) —
    never numeric scores and never fabricated assertions.
    """
    total = evaluation_summary.total_answers or 1
    dimensions = (
        ("Coverage", evaluation_summary.coverage, "answers addressed the question intent"),
        ("Evidence", evaluation_summary.evidence, "answers were grounded in canonical profile evidence"),
        ("Claim alignment", evaluation_summary.claim_alignment, "answers aligned with the question competencies"),
        ("Measurability", evaluation_summary.measurability, "answers included a measurable outcome"),
        ("Structure", evaluation_summary.structure, "answers followed a structured (STAR) narrative"),
    )
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    for name, count, qualifier in dimensions:
        if count > 0:
            strengths.append(f"{name}: {count} of {total} {qualifier}.")
        if count < total:
            weaknesses.append(f"{name}: only {count} of {total} {qualifier}.")
    if evaluation_summary.inconsistent_answers:
        weaknesses.append(
            f"Consistency: {evaluation_summary.inconsistent_answers} answer(s) "
            "contained contradictory or unsupported claims."
        )
    if weaknesses:
        recommendations.append(
            "Ground answers in canonical profile evidence and keep claims consistent."
        )
        if evaluation_summary.measurability < total:
            recommendations.append(
                "Include a measurable outcome (metric, percentage, or business result) in each answer."
            )
        if evaluation_summary.structure < total:
            recommendations.append(
                "Structure answers around Situation, Task, Action, and Result (STAR)."
            )

    return InterviewReport(
        id=f"{session.id}:report",
        session_id=session.id,
        profile_id=session.profile_id,
        plan_ref=session.plan_ref,
        summary=session.summary or SessionEngine().build_summary(session),
        session_metrics=session.metrics or SessionMetrics(),
        answers=session.answers,
        strengths=tuple(strengths),
        weaknesses=tuple(weaknesses),
        recommendations=tuple(recommendations),
    )
