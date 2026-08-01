"""Interview Intelligence — deterministic foundation (M1.14).

A Core consumer module (ADR-005): domain models + a deterministic question
engine that turns a canonical profile into an evidence-backed ``InterviewPlan``.
No LLM, no REST, no frontend — the future AI layer will enrich question prose
and answer outlines without redesigning this foundation.
"""

from __future__ import annotations

from .competency import CompetencyMapper
from .domain import (
    CATEGORY_ORDER,
    Competency,
    EvidenceCitation,
    InterviewPlan,
    InterviewQuestion,
    PreparationGuide,
    QuestionType,
    SuggestedAnswer,
)
from .engine import InterviewEngine, build_preparation_plan
from .exceptions import (
    InterviewError,
    InvalidProfileError,
    UnsupportedQuestionTypeError,
)
from .question_builder import QuestionBuilder
from .templates import (
    QUESTION_TEMPLATES,
    QuestionTemplate,
    template_for,
    templates_for,
)

__all__ = [
    "InterviewEngine",
    "build_preparation_plan",
    "CompetencyMapper",
    "QuestionBuilder",
    "QuestionType",
    "CATEGORY_ORDER",
    "Competency",
    "EvidenceCitation",
    "InterviewPlan",
    "InterviewQuestion",
    "PreparationGuide",
    "SuggestedAnswer",
    "QuestionTemplate",
    "QUESTION_TEMPLATES",
    "template_for",
    "templates_for",
    "InterviewError",
    "InvalidProfileError",
    "UnsupportedQuestionTypeError",
]
