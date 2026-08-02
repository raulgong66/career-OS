"""Interview Simulation — domain package (ADR-007, M1.17.2 / M1.17.3).

Runtime models and the session engine for an interview simulation.  No
evaluation engine, no REST API, no persistence — only typed domain objects,
serialization, and deterministic orchestration.
"""

from __future__ import annotations

from .domain import (
    AnswerEvaluation,
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
from .exceptions import (
    InterviewSessionError,
    InvalidAnswerError,
    InvalidPlanError,
    InvalidSessionStateError,
    NoActiveQuestionError,
)

__all__ = [
    "AnswerEvaluation",
    "InterviewAnswer",
    "InterviewFeedback",
    "InterviewQuestionInstance",
    "InterviewReport",
    "InterviewSession",
    "InterviewSessionError",
    "InterviewSummary",
    "InvalidAnswerError",
    "InvalidPlanError",
    "InvalidSessionStateError",
    "NoActiveQuestionError",
    "SessionEngine",
    "SessionMetrics",
    "SessionState",
]