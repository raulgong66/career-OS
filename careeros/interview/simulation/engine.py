"""Interview Simulation session lifecycle engine."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from careeros.interview.domain import InterviewPlan
from .domain import InterviewAnswer, InterviewSession, InterviewSessionState
from .evaluation import EvaluationEngine, EvaluationSummary
from .exceptions import (
    InvalidAnswerError,
    InvalidQuestionError,
    InvalidSessionStateError,
    NoActiveQuestionError,
)
from .report import InterviewReport, build_report


class SessionEngine:
    """Runtime engine for interview sessions."""

    def __init__(self, evaluation_engine: EvaluationEngine | None = None) -> None:
        self.evaluation_engine = evaluation_engine or EvaluationEngine()

    def create_session(
        self,
        plan: InterviewPlan,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> InterviewSession:
        if not hasattr(plan, "question_count"):
            raise InvalidSessionStateError("InterviewPlan is required to create a session")
        return InterviewSession(
            session_id=session_id,
            plan=plan,
            current_question_index=0,
            answers=(),
            state=InterviewSessionState.DRAFT,
            metadata=metadata or {},
        )

    def start_session(self, session: InterviewSession) -> InterviewSession:
        if session.state not in (InterviewSessionState.DRAFT, InterviewSessionState.READY):
            raise InvalidSessionStateError(
                f"Cannot start session from state: {session.state.value}"
            )
        if session.question_count == 0:
            return replace(session, state=InterviewSessionState.COMPLETED)
        return replace(session, state=InterviewSessionState.IN_PROGRESS)

    def submit_answer(self, session: InterviewSession, answer: InterviewAnswer) -> InterviewSession:
        if session.state != InterviewSessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                "Cannot submit answer when session is not in progress"
            )
        current_question = session.current_question_instance()
        if current_question is None:
            raise NoActiveQuestionError("No active question to answer")
        if answer.question_id != current_question.question.id:
            raise InvalidQuestionError("Submitted answer does not match the active question")
        if any(existing.question_id == answer.question_id for existing in session.answers):
            raise InvalidAnswerError("Answer for this question has already been submitted")

        return replace(session, answers=session.answers + (answer,))

    def next_question(self, session: InterviewSession) -> InterviewSession:
        if session.state != InterviewSessionState.IN_PROGRESS:
            raise InvalidSessionStateError(
                "Cannot advance question when session is not in progress"
            )
        if session.current_question_index >= session.question_count:
            raise NoActiveQuestionError("No active question to advance")

        next_index = session.current_question_index + 1
        if next_index >= session.question_count:
            return self.complete_session(session)
        return replace(session, current_question_index=next_index)

    def pause_session(self, session: InterviewSession) -> InterviewSession:
        if session.state != InterviewSessionState.IN_PROGRESS:
            raise InvalidSessionStateError("Only in-progress sessions can be paused")
        return replace(session, state=InterviewSessionState.PAUSED)

    def resume_session(self, session: InterviewSession) -> InterviewSession:
        if session.state != InterviewSessionState.PAUSED:
            raise InvalidSessionStateError("Only paused sessions can be resumed")
        return replace(session, state=InterviewSessionState.IN_PROGRESS)

    def complete_session(self, session: InterviewSession) -> InterviewSession:
        if session.state not in (
            InterviewSessionState.IN_PROGRESS,
            InterviewSessionState.PAUSED,
            InterviewSessionState.READY,
        ):
            raise InvalidSessionStateError(
                f"Cannot complete session from state: {session.state.value}"
            )
        return replace(session, state=InterviewSessionState.COMPLETED)

    def build_summary(self, session: InterviewSession) -> EvaluationSummary:
        if session.state not in (
            InterviewSessionState.COMPLETED,
            InterviewSessionState.REVIEWED,
        ):
            raise InvalidSessionStateError(
                "Session must be completed before building a summary"
            )
        evaluations = tuple(
            self.evaluation_engine.evaluate_answer(question, answer)
            for question, answer in zip(session.plan.questions, session.answers)
        )
        return self.evaluation_engine.summarize(
            session_id=session.session_id,
            question_count=session.question_count,
            evaluations=evaluations,
        )

    def build_report(self, session: InterviewSession) -> InterviewReport:
        summary = self.build_summary(session)
        return build_report(session, summary)
