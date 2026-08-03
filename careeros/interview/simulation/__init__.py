"""Interview Simulation domain package."""

from __future__ import annotations

from .domain import (
    InterviewAnswer,
    InterviewQuestionInstance,
    InterviewSession,
    InterviewSessionState,
    SessionMetrics,
)
from .engine import SessionEngine
from .evaluation import (
    AnswerEvaluation,
    EvaluationEngine,
    EvaluationSummary,
    FeedbackSeverity,
    InterviewFeedback,
)
from .exceptions import (
    EvaluationPreconditionError,
    InvalidAnswerError,
    InvalidQuestionError,
    InvalidSessionStateError,
    MissingEvidenceReferenceError,
    NoActiveQuestionError,
)
from .report import InterviewReport, InterviewSummary, attach_summary, build_report

__all__ = [
    "AnswerEvaluation",
    "EvaluationEngine",
    "EvaluationSummary",
    "EvaluationPreconditionError",
    "FeedbackSeverity",
    "InterviewAnswer",
    "InterviewFeedback",
    "InterviewQuestionInstance",
    "InterviewReport",
    "InterviewSession",
    "InterviewSessionState",
    "InterviewSummary",
    "MissingEvidenceReferenceError",
    "NoActiveQuestionError",
    "SessionEngine",
    "SessionMetrics",
    "attach_summary",
    "build_report",
]
