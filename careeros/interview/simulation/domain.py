"""Interview Simulation — domain models (ADR-007).

Runtime objects for an interview simulation session.  All professional
knowledge remains owned by the canonical profile; these objects reference
it through ADR-002 evidence citations (``EvidenceCitation.source_ref()``)
and never duplicate profile data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..domain import EvidenceCitation, SuggestedAnswer


class SessionState(str, Enum):
    """The lifecycle states of an interview simulation session.

    Transitions are enforced by the future session engine (not this
    milestone); the enum only defines the valid state values.
    """

    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class SessionMetrics:
    """Aggregate runtime statistics for a simulation session.

    Computed deterministically from the session's answers; no subjective
    evaluation data is stored here.
    """

    total_questions: int = 0
    answered_questions: int = 0
    average_duration_seconds: int | None = None
    total_duration_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "answered_questions": self.answered_questions,
            "average_duration_seconds": self.average_duration_seconds,
            "total_duration_seconds": self.total_duration_seconds,
        }


@dataclass(frozen=True)
class AnswerEvaluation:
    """Deterministic signal vector computed from an answer text.

    Each field is a boolean flag produced by a pure function over the
    answer text and the question's expected content.  No AI, no scoring,
    no numeric aggregate — consistent with ADR-003's qualitative approach.
    """

    covers_claim: bool = False
    has_metric: bool = False
    cites_evidence: bool = False
    follows_structure: bool = False
    matches_question_competencies: bool = False
    citations: tuple[EvidenceCitation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "covers_claim": self.covers_claim,
            "has_metric": self.has_metric,
            "cites_evidence": self.cites_evidence,
            "follows_structure": self.follows_structure,
            "matches_question_competencies": self.matches_question_competencies,
            "citations": [c.to_dict() for c in self.citations],
        }


@dataclass(frozen=True)
class InterviewFeedback:
    """Structured, per-answer feedback for an interview session.

    Follows the ADR-003 qualitative model: no numeric score, only
    categorical / textual guidance.  ``citations`` reference the canonical
    profile elements detected in (or suggested for) the answer.
    """

    id: str
    question_id: str
    answer_id: str
    missing: tuple[str, ...] = ()
    improvement_recommendation: str | None = None
    citations: tuple[EvidenceCitation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question_id": self.question_id,
            "answer_id": self.answer_id,
            "missing": list(self.missing),
            "improvement_recommendation": self.improvement_recommendation,
            "citations": [c.to_dict() for c in self.citations],
        }


@dataclass(frozen=True)
class InterviewAnswer:
    """A candidate's response to a single question within a session.

    The answer is immutable once recorded.  The ``evaluation`` and
    ``feedback`` fields are populated deterministically by the evaluation
    engine (not by this milestone).
    """

    id: str
    session_id: str
    question_id: str
    text: str
    answered_at: str | None = None
    duration_seconds: int | None = None
    evaluation: AnswerEvaluation | None = None
    feedback: InterviewFeedback | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "session_id": self.session_id,
            "question_id": self.question_id,
            "text": self.text,
            "answered_at": self.answered_at,
            "duration_seconds": self.duration_seconds,
        }
        if self.evaluation is not None:
            result["evaluation"] = self.evaluation.to_dict()
        if self.feedback is not None:
            result["feedback"] = self.feedback.to_dict()
        return result


@dataclass(frozen=True)
class InterviewQuestionInstance:
    """A question as instantiated within a specific session.

    References canonical knowledge through ``evidence_citations``
    (``EvidenceCitation`` with ADR-002 ``source_ref()``) and
    ``context_refs`` (``{id, type}`` pairs).  Never contains profile data.
    """

    id: str
    session_id: str
    question_text: str
    category: str
    difficulty: str = "intermediate"
    competency_ids: tuple[str, ...] = ()
    context_refs: tuple[dict[str, str], ...] = ()
    evidence_citations: tuple[EvidenceCitation, ...] = ()
    suggested_answer: SuggestedAnswer | None = None
    order: int = 0
    time_limit_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "session_id": self.session_id,
            "question_text": self.question_text,
            "category": self.category,
            "difficulty": self.difficulty,
            "competency_ids": list(self.competency_ids),
            "context_refs": [dict(ref) for ref in self.context_refs],
            "evidence_citations": [c.to_dict() for c in self.evidence_citations],
            "order": self.order,
            "time_limit_seconds": self.time_limit_seconds,
        }
        if self.suggested_answer is not None:
            result["suggested_answer"] = self.suggested_answer.to_dict()
        return result


@dataclass(frozen=True)
class InterviewSummary:
    """Aggregate assessment summary for a completed session.

    All counts are derived deterministically from the session's answers
    and their evaluations.  The ``strong_answers`` / ``weak_answers``
    counts follow the qualitative levels defined in ADR-003, never stored
    numeric scores.
    """

    total_questions: int = 0
    answered_questions: int = 0
    covered_claims: int = 0
    metric_citations: int = 0
    evidence_citations: int = 0
    structured_answers: int = 0
    strong_answers: int = 0
    weak_answers: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "answered_questions": self.answered_questions,
            "covered_claims": self.covered_claims,
            "metric_citations": self.metric_citations,
            "evidence_citations": self.evidence_citations,
            "structured_answers": self.structured_answers,
            "strong_answers": self.strong_answers,
            "weak_answers": self.weak_answers,
        }


@dataclass(frozen=True)
class InterviewSession:
    """A planned or in-progress interview simulation (runtime object).

    The session is the runtime container for an interview.  It references
    the deterministic ``InterviewPlan`` via ``plan_ref`` and never owns
    profile or question-engine data — those stay in the Knowledge layer.

    ``started_at``, ``paused_at``, and ``completed_at`` are ISO-8601
    timestamps set by the future session engine.
    """

    id: str
    plan_ref: str
    profile_id: str
    state: SessionState = SessionState.DRAFT
    questions: tuple[InterviewQuestionInstance, ...] = ()
    answers: tuple[InterviewAnswer, ...] = ()
    started_at: str | None = None
    completed_at: str | None = None
    paused_at: str | None = None
    metrics: SessionMetrics | None = None
    summary: InterviewSummary | None = None
    metadata: dict[str, Any] | None = None

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def answer_count(self) -> int:
        return len(self.answers)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "plan_ref": self.plan_ref,
            "profile_id": self.profile_id,
            "state": self.state.value,
            "questions": [q.to_dict() for q in self.questions],
            "answers": [a.to_dict() for a in self.answers],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "paused_at": self.paused_at,
        }
        if self.metrics is not None:
            result["metrics"] = self.metrics.to_dict()
        if self.summary is not None:
            result["summary"] = self.summary.to_dict()
        if self.metadata is not None:
            result["metadata"] = dict(self.metadata)
        return result

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass(frozen=True)
class InterviewReport:
    """Immutable outcome of a completed simulation session.

    The report is an export-oriented view: it references the session by
    ``session_id`` and carries the aggregate evaluation data.  Detailed
    per-question feedback lives on the session's ``InterviewAnswer``
    objects.
    """

    id: str
    session_id: str
    profile_id: str
    plan_ref: str
    summary: InterviewSummary
    session_metrics: SessionMetrics
    answers: tuple[InterviewAnswer, ...] = ()
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "plan_ref": self.plan_ref,
            "summary": self.summary.to_dict(),
            "session_metrics": self.session_metrics.to_dict(),
            "answers": [a.to_dict() for a in self.answers],
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "recommendations": list(self.recommendations),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)