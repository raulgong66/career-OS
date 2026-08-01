"""Interview Intelligence — domain exceptions.

Interview Intelligence is a Core consumer module (ADR-005 / ADR-004): its
errors extend the Core exception hierarchy and never re-implement it.
"""

from __future__ import annotations

from careeros.exceptions import CareerOSException


class InterviewError(CareerOSException):
    """Base error for the Interview Intelligence module."""


class InvalidProfileError(InterviewError):
    """Raised when the interview engine receives an unusable canonical profile."""


class UnsupportedQuestionTypeError(InterviewError):
    """Raised when a question category has no registered templates."""
