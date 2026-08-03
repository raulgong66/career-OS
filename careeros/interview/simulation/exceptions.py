"""Interview Simulation domain exceptions."""

from __future__ import annotations


class InterviewSimulationError(Exception):
    """Base exception for Interview Simulation domain errors."""


class InvalidSessionStateError(InterviewSimulationError):
    pass


class InvalidAnswerError(InterviewSimulationError):
    pass


class InvalidQuestionError(InterviewSimulationError):
    pass


class NoActiveQuestionError(InterviewSimulationError):
    pass


class EvaluationPreconditionError(InterviewSimulationError):
    pass


class MissingEvidenceReferenceError(InterviewSimulationError):
    pass
