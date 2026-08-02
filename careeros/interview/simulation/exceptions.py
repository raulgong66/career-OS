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


class InvalidQuestionError(InterviewSessionError):
    """Raised when the question context for an answer is missing or
    mismatched (e.g. the question does not belong to the session or does
    not match the answer)."""


class MissingEvidenceReferenceError(InterviewSessionError):
    """Raised when a cited evidence reference is invalid or not canonical
    (ADR-002): malformed ``{id,type}`` citations, non-canonical element
    types, or session-owned fragments used as evidence."""


class InvalidClaimError(InterviewSessionError):
    """Raised when claim validation cannot proceed due to missing claim
    metadata (ADR-003): malformed competency or context references."""


class EvaluationPreconditionError(InterviewSessionError):
    """Raised when required context or Core services are unavailable for
    evaluation (e.g. a supplied rule registry lacks the evaluation rules)."""