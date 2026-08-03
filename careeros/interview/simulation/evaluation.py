"""Deterministic evaluation foundation for Interview Simulation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from careeros.interview.domain import InterviewQuestion

from .domain import InterviewAnswer
from .exceptions import (
    EvaluationPreconditionError,
    InvalidAnswerError,
    InvalidQuestionError,
    MissingEvidenceReferenceError,
)


class FeedbackSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class InterviewFeedback:
    code: str
    message: str
    severity: FeedbackSeverity = FeedbackSeverity.INFO

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
        }


@dataclass(frozen=True)
class AnswerEvaluation:
    question_id: str
    coverage_score: int
    evidence_score: int
    structure_score: int
    overall_score: int
    feedback: tuple[InterviewFeedback, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "question_id": self.question_id,
            "coverage_score": self.coverage_score,
            "evidence_score": self.evidence_score,
            "structure_score": self.structure_score,
            "overall_score": self.overall_score,
            "feedback": [item.to_dict() for item in self.feedback],
        }


@dataclass(frozen=True)
class EvaluationSummary:
    session_id: str
    question_count: int
    answered_questions: int
    average_score: int
    evaluations: tuple[AnswerEvaluation, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "question_count": self.question_count,
            "answered_questions": self.answered_questions,
            "average_score": self.average_score,
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
        }


_SUMMARY_KEYWORDS = {
    "technical": ("code", "system", "architecture", "design", "deploy", "scal", "service", "platform"),
    "behavioral": ("team", "collaborat", "communicat", "stakeholder", "challenge", "resolve", "decision", "problem"),
    "leadership": ("lead", "managed", "initiative", "strategy", "vision", "direction", "mentor", "stakeholder"),
    "project_deep_dive": ("project", "scope", "delivery", "implementation", "challenge", "outcome", "impact"),
    "problem_solving": ("problem", "analysis", "solution", "tradeoff", "issue", "debug", "optimi"),
    "career_motivation": ("motivated", "goal", "career", "passion", "growth", "role", "impact"),
}

_STRUCTURE_WORDS = (
    "led",
    "built",
    "implemented",
    "designed",
    "reduced",
    "improved",
    "measured",
    "delivered",
    "resolved",
    "owned",
)


class EvaluationEngine:
    """Deterministic evaluation engine for interview answers."""

    def evaluate_answer(
        self, question: InterviewQuestion, answer: InterviewAnswer
    ) -> AnswerEvaluation:
        if not isinstance(answer, InterviewAnswer):
            raise InvalidAnswerError("Answer must be an InterviewAnswer")
        if question.id != answer.question_id:
            raise InvalidQuestionError(
                "Answer question_id does not match the active question"
            )
        if question.evidence_citations and not answer.evidence_references:
            raise MissingEvidenceReferenceError(
                "Expected at least one canonical evidence reference"
            )

        text = self._normalize(answer.text)
        if not text:
            raise InvalidAnswerError("Answer text must not be empty")

        coverage_score = self._coverage_score(question, text)
        evidence_score = self._evidence_score(question, answer.evidence_references)
        structure_score = self._structure_score(text)
        overall_score = int(round((coverage_score + evidence_score + structure_score) / 3))
        feedback = self._build_feedback(
            coverage_score, evidence_score, structure_score
        )

        return AnswerEvaluation(
            question_id=question.id,
            coverage_score=coverage_score,
            evidence_score=evidence_score,
            structure_score=structure_score,
            overall_score=overall_score,
            feedback=tuple(feedback),
        )

    def summarize(
        self, session_id: str, question_count: int, evaluations: Sequence[AnswerEvaluation]
    ) -> "EvaluationSummary":
        if question_count < 0:
            raise EvaluationPreconditionError("Question count must be non-negative")
        if not evaluations:
            return EvaluationSummary(
                session_id=session_id,
                question_count=question_count,
                answered_questions=0,
                average_score=0,
                evaluations=(),
            )

        average_score = int(round(sum(e.overall_score for e in evaluations) / len(evaluations)))
        return EvaluationSummary(
            session_id=session_id,
            question_count=question_count,
            answered_questions=len(evaluations),
            average_score=average_score,
            evaluations=tuple(evaluations),
        )

    def _coverage_score(self, question: InterviewQuestion, text: str) -> int:
        keywords = _SUMMARY_KEYWORDS.get(question.category.value, ())
        if not keywords:
            return 50
        matches = sum(1 for keyword in keywords if keyword in text)
        return min(100, int(matches * (100 / max(len(keywords), 1))))

    def _evidence_score(self, question: InterviewQuestion, evidence_references: Sequence[dict[str, str]]) -> int:
        if not question.evidence_citations:
            return 100
        canonical_refs = {tuple(c.source_ref().items()) for c in question.evidence_citations}
        provided_refs = {tuple(ref.items()) for ref in evidence_references}
        matched = len(canonical_refs & provided_refs)
        return min(100, int((matched / max(len(canonical_refs), 1)) * 100))

    def _structure_score(self, text: str) -> int:
        matched = sum(1 for word in _STRUCTURE_WORDS if word in text)
        if len(text) < 50:
            return min(100, matched * 20)
        return min(100, matched * 25 + 25)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    def _build_feedback(
        self,
        coverage_score: int,
        evidence_score: int,
        structure_score: int,
    ) -> list[InterviewFeedback]:
        feedback: list[InterviewFeedback] = []
        if coverage_score < 50:
            feedback.append(
                InterviewFeedback(
                    code="coverage_low",
                    message="Answer should address the question intent more directly.",
                    severity=FeedbackSeverity.WARNING,
                )
            )
        if evidence_score < 50:
            feedback.append(
                InterviewFeedback(
                    code="evidence_weak",
                    message="Include canonical evidence references to support the response.",
                    severity=FeedbackSeverity.WARNING,
                )
            )
        if structure_score < 50:
            feedback.append(
                InterviewFeedback(
                    code="structure_weak",
                    message="Use a clear, action-oriented response structure.",
                    severity=FeedbackSeverity.INFO,
                )
            )
        if not feedback:
            feedback.append(
                InterviewFeedback(
                    code="strong_answer",
                    message="The response is well-aligned and evidence-backed.",
                    severity=FeedbackSeverity.INFO,
                )
            )
        return feedback
