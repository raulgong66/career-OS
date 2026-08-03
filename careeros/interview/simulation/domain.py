"""Interview Simulation runtime domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from careeros.interview.domain import InterviewPlan, InterviewQuestion


class InterviewSessionState(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class InterviewAnswer:
    question_id: str
    text: str
    evidence_references: tuple[dict[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "text": self.text,
            "evidence_references": [dict(ref) for ref in self.evidence_references],
        }


@dataclass(frozen=True)
class InterviewQuestionInstance:
    question: InterviewQuestion
    index: int
    total: int

    @property
    def is_active(self) -> bool:
        return self.index <= self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "total": self.total,
            "question": self.question.to_dict(),
        }


@dataclass(frozen=True)
class SessionMetrics:
    question_count: int
    answered_questions: int
    evidence_reference_count: int
    average_score: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_count": self.question_count,
            "answered_questions": self.answered_questions,
            "evidence_reference_count": self.evidence_reference_count,
            "average_score": self.average_score,
        }


@dataclass(frozen=True)
class InterviewSession:
    session_id: str
    plan: InterviewPlan
    current_question_index: int = 0
    answers: tuple[InterviewAnswer, ...] = ()
    state: InterviewSessionState = InterviewSessionState.DRAFT
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def question_count(self) -> int:
        return self.plan.question_count

    @property
    def answered_count(self) -> int:
        return len(self.answers)

    @property
    def has_active_question(self) -> bool:
        return (
            self.state == InterviewSessionState.IN_PROGRESS
            and self.current_question_index < self.question_count
        )

    def current_question_instance(self) -> InterviewQuestionInstance | None:
        if not self.has_active_question:
            return None
        return InterviewQuestionInstance(
            question=self.plan.questions[self.current_question_index],
            index=self.current_question_index + 1,
            total=self.question_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "current_question_index": self.current_question_index,
            "question_count": self.question_count,
            "answered_count": self.answered_count,
            "answers": [answer.to_dict() for answer in self.answers],
            "metadata": dict(self.metadata),
        }
