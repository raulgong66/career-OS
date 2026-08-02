"""Interview Simulation — domain exceptions (ADR-007).

All exceptions extend the Interview Intelligence error hierarchy
(``InterviewError``), which itself extends ``CareerOSException``, so
callers can catch at any level.
"""

from __future__ import annotations

from ..exceptions import InterviewError


class InterviewSessionError(InterviewError):
    """Base error for the Interview Simulation subsystem."""


class InvalidSessionStateError(InterviewSessionError):
    """Raised when a session transition is attempted with an invalid current
    state for the requested operation."""


class InvalidAnswerError(InterviewSessionError):
    """Raised when an answer fails validation (e.g. empty text, wrong session,
    unknown question)."""


class InvalidPlanError(InterviewSessionError):
    """Raised when a session cannot be created from an invalid or
    incompatible ``InterviewPlan``."""


class NoActiveQuestionError(InterviewSessionError):
    """Raised when no active question remains in the session (the question
    sequence is exhausted)."""