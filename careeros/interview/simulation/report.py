"""Interview Simulation report and summary types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evaluation import EvaluationSummary, InterviewFeedback
from .domain import InterviewSession


@dataclass(frozen=True)
class InterviewSummary:
    session_id: str
    question_count: int
    answered_questions: int
    average_score: int
    feedback: tuple[InterviewFeedback, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "question_count": self.question_count,
            "answered_questions": self.answered_questions,
            "average_score": self.average_score,
            "feedback": [item.to_dict() for item in self.feedback],
        }


@dataclass(frozen=True)
class InterviewReport:
    session_id: str
    summary: InterviewSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "summary": self.summary.to_dict(),
        }


def build_report(session: InterviewSession, summary: EvaluationSummary) -> InterviewReport:
    return InterviewReport(
        session_id=session.session_id,
        summary=InterviewSummary(
            session_id=summary.session_id,
            question_count=summary.question_count,
            answered_questions=summary.answered_questions,
            average_score=summary.average_score,
            feedback=tuple(
                feedback
                for evaluation in summary.evaluations
                for feedback in evaluation.feedback
            ),
        ),
    )


def attach_summary(session: InterviewSession, summary: EvaluationSummary) -> InterviewReport:
    return build_report(session, summary)
