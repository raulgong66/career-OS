"""Interview Simulation — domain package (ADR-007, M1.17.2–M1.17.4).

Runtime models, the session engine, and the answer evaluation engine for an
interview simulation.  No REST API, no persistence, no AI — only typed domain
objects, serialization, deterministic orchestration, and deterministic answer
analysis.
"""

from __future__ import annotations

from .domain import (
    AnswerEvaluation,
    EvaluationSummary,
    InterviewAnswer,
    InterviewFeedback,
    InterviewQuestionInstance,
    InterviewReport,
    InterviewSession,
    InterviewSummary,
    SessionMetrics,
    SessionState,
)
from .engine import SessionEngine
from .evaluation import EVALUATION_RULE_IDS, EvaluationEngine
from .exceptions import (
    EvaluationPreconditionError,
    InterviewSessionError,
    InvalidAnswerError,
    InvalidClaimError,
    InvalidPlanError,
    InvalidQuestionError,
    InvalidSessionStateError,
    MissingEvidenceReferenceError,
    NoActiveQuestionError,
)

__all__ = [
    "AnswerEvaluation",
    "EVALUATION_RULE_IDS",
    "EvaluationEngine",
    "EvaluationPreconditionError",
    "EvaluationSummary",
    "InterviewAnswer",
    "InterviewFeedback",
    "InterviewQuestionInstance",
    "InterviewReport",
    "InterviewSession",
    "InterviewSessionError",
    "InterviewSummary",
    "InvalidAnswerError",
    "InvalidClaimError",
    "InvalidPlanError",
    "InvalidQuestionError",
    "InvalidSessionStateError",
    "MissingEvidenceReferenceError",
    "NoActiveQuestionError",
    "SessionEngine",
    "SessionMetrics",
    "SessionState",
]