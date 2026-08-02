"""Interview Simulation — session engine (ADR-007, M1.17.3).

Deterministic orchestration of an interview simulation session per
``docs/platform-beta/interview-simulation/07-session-engine-design.md``.

The engine owns orchestration only:

- creating sessions from an ``InterviewPlan``
- advancing session state through the documented lifecycle
- selecting the next question
- recording answers against the active question
- building session metrics and an ``InterviewSummary`` from completed state

The engine explicitly does NOT evaluate answers, generate AI feedback, persist
state, expose transport, or mutate the canonical profile.  It is stateless:
every method receives the session explicitly and returns the updated session
(or a query result), keeping orchestration deterministic and safe in
worker/request contexts where each session is passed explicitly.
"""

from __future__ import annotations

from typing import Any

from ..domain import InterviewPlan
from .domain import (
    InterviewAnswer,
    InterviewQuestionInstance,
    InterviewSession,
    InterviewSummary,
    SessionMetrics,
    SessionState,
)
from .exceptions import (
    InvalidAnswerError,
    InvalidPlanError,
    InvalidSessionStateError,
    NoActiveQuestionError,
)


def _active_question(session: InterviewSession) -> InterviewQuestionInstance | None:
    """The question the session is currently on, or None when exhausted."""
    if session.answer_count >= session.question_count:
        return None
    return session.questions[session.answer_count]


def _compute_metrics(session: InterviewSession) -> SessionMetrics:
    durations = [
        answer.duration_seconds
        for answer in session.answers
        if answer.duration_seconds is not None
    ]
    total = sum(durations)
    return SessionMetrics(
        total_questions=session.question_count,
        answered_questions=session.answer_count,
        average_duration_seconds=(total / len(durations)) if durations else None,
        total_duration_seconds=total if durations else None,
    )


class SessionEngine:
    """Deterministic session orchestration (ADR-007).

    All state is passed in and returned explicitly; the engine keeps no
    instance state so the same inputs always produce the same outputs.
    """

    def create_session(
        self,
        plan: InterviewPlan,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> InterviewSession:
        """Create a ``Draft`` session from an ``InterviewPlan``.

        Question instances are materialized from the plan in order.  The
        session only references canonical knowledge (via the plan's existing
        evidence citations / context refs); it never duplicates profile data.
        """
        if not isinstance(plan, InterviewPlan):
            raise InvalidPlanError(
                "Cannot create a session from a non-InterviewPlan "
                f"(got {type(plan).__name__})."
            )
        if not plan.person_id:
            raise InvalidPlanError(
                "Cannot create a session from a plan without a person id."
            )
        questions = tuple(
            InterviewQuestionInstance(
                id=f"{session_id}:{question.id}",
                session_id=session_id,
                question_text=question.text,
                category=question.category.value,
                difficulty=question.difficulty,
                competency_ids=question.competency_ids,
                context_refs=question.context_refs,
                evidence_citations=question.evidence_citations,
                suggested_answer=question.suggested_answer,
                order=order,
                time_limit_seconds=None,
            )
            for order, question in enumerate(plan.questions)
        )
        return InterviewSession(
            id=session_id,
            plan_ref=self._plan_ref(plan),
            profile_id=plan.person_id,
            state=SessionState.DRAFT,
            questions=questions,
            metadata=metadata,
        )

    def start_session(self, session: InterviewSession) -> InterviewSession:
        """Advance a session into ``InProgress``.

        Accepts ``Draft`` (moving through ``Ready`` first, per the lifecycle
        sequence) or ``Ready`` sessions; anything else is an invalid start.
        """
        self._require_state(session, {SessionState.DRAFT, SessionState.READY}, "start")
        return self._transition(session, SessionState.IN_PROGRESS)

    def next_question(self, session: InterviewSession) -> InterviewQuestionInstance:
        """Return the next unanswered question in the session sequence.

        Raises :class:`NoActiveQuestionError` when the sequence is exhausted
        (the deterministic completion signal for the caller).
        """
        self._require_state(session, {SessionState.IN_PROGRESS}, "select a question for")
        question = _active_question(session)
        if question is None:
            raise NoActiveQuestionError(
                f"Session '{session.id}' has no active question: all "
                f"{session.question_count} questions are already answered."
            )
        return question

    def submit_answer(
        self,
        session: InterviewSession,
        answer: InterviewAnswer,
    ) -> InterviewSession:
        """Record an answer against the active question and refresh metrics.

        The session must be ``InProgress``, the answer must belong to this
        session, target the active question, and carry non-empty text.
        """
        self._require_state(session, {SessionState.IN_PROGRESS}, "accept answers for")
        self._validate_answer(session, answer)
        updated = _replace(session, answers=session.answers + (answer,))
        return _replace(updated, metrics=_compute_metrics(updated))

    def pause_session(self, session: InterviewSession) -> InterviewSession:
        """Temporarily suspend an in-progress session."""
        self._require_state(session, {SessionState.IN_PROGRESS}, "pause")
        return self._transition(session, SessionState.PAUSED)

    def resume_session(self, session: InterviewSession) -> InterviewSession:
        """Resume a paused session."""
        self._require_state(session, {SessionState.PAUSED}, "resume")
        return self._transition(session, SessionState.IN_PROGRESS)

    def complete_session(self, session: InterviewSession) -> InterviewSession:
        """Mark a session ``Completed`` with final metrics.

        Allowed from ``Ready`` (fast-path, zero answers), ``InProgress``, or
        ``Paused``.  Completed, Reviewed, and Archived sessions are final.
        """
        self._require_state(
            session,
            {SessionState.READY, SessionState.IN_PROGRESS, SessionState.PAUSED},
            "complete",
        )
        return _replace(
            session,
            state=SessionState.COMPLETED,
            metrics=_compute_metrics(session),
        )

    def build_summary(self, session: InterviewSession) -> InterviewSummary:
        """Build an ``InterviewSummary`` from completed session state.

        Counts are derived deterministically from the session's answers and,
        where present, their ``AnswerEvaluation`` signals.
        """
        self._require_state(session, {SessionState.COMPLETED}, "build a summary for")
        evaluations = [
            answer.evaluation
            for answer in session.answers
            if answer.evaluation is not None
        ]
        return InterviewSummary(
            total_questions=session.question_count,
            answered_questions=session.answer_count,
            covered_claims=sum(1 for e in evaluations if e.covers_claim),
            metric_citations=sum(1 for e in evaluations if e.has_metric),
            evidence_citations=sum(1 for e in evaluations if e.cites_evidence),
            structured_answers=sum(1 for e in evaluations if e.follows_structure),
            strong_answers=sum(1 for e in evaluations if e.covers_claim and e.cites_evidence),
            weak_answers=sum(1 for e in evaluations if not e.covers_claim),
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _plan_ref(plan: InterviewPlan) -> str:
        """Deterministic reference to the plan's identity.

        ``InterviewPlan`` carries no stable id; the reference is derived from
        the plan's identity fields so the same plan always maps to the same
        reference (see completion report / implementation note).
        """
        target = plan.target_role or "general"
        return f"{plan.person_id}:{plan.profile_version}:{target}"

    @staticmethod
    def _validate_answer(session: InterviewSession, answer: InterviewAnswer) -> None:
        if not isinstance(answer, InterviewAnswer):
            raise InvalidAnswerError(
                f"Cannot record a non-InterviewAnswer ({type(answer).__name__})."
            )
        if not answer.text or not answer.text.strip():
            raise InvalidAnswerError("Cannot record an empty answer.")
        if answer.session_id != session.id:
            raise InvalidAnswerError(
                f"Answer for session '{answer.session_id}' does not belong to "
                f"session '{session.id}'."
            )
        question = _active_question(session)
        if question is None:
            raise InvalidAnswerError(
                f"Session '{session.id}' has no active question to answer."
            )
        if answer.question_id != question.id:
            raise InvalidAnswerError(
                f"Answer targets question '{answer.question_id}' but the active "
                f"question is '{question.id}'."
            )

    @staticmethod
    def _require_state(
        session: InterviewSession,
        allowed: set[SessionState],
        action: str,
    ) -> None:
        if session.state not in allowed:
            expected = ", ".join(sorted(state.value for state in allowed))
            raise InvalidSessionStateError(
                f"Cannot {action} a session in state '{session.state.value}'; "
                f"expected one of: {expected}."
            )

    @staticmethod
    def _transition(
        session: InterviewSession,
        target: SessionState,
    ) -> InterviewSession:
        return _replace(session, state=target)


def _replace(session: InterviewSession, **changes: Any) -> InterviewSession:
    """Immutable-copy of the session with the given fields replaced."""
    fields: dict[str, Any] = {
        "id": session.id,
        "plan_ref": session.plan_ref,
        "profile_id": session.profile_id,
        "state": session.state,
        "questions": session.questions,
        "answers": session.answers,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "paused_at": session.paused_at,
        "metrics": session.metrics,
        "summary": session.summary,
        "metadata": session.metadata,
    }
    fields.update(changes)
    return InterviewSession(**fields)
