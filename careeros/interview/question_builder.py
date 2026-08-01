"""Interview Intelligence — question instantiation and answer outlines.

``QuestionBuilder`` renders templates with verbatim profile excerpts and builds
structured ``SuggestedAnswer`` outlines (Situation/Task/Action/Result/Evidence/
Achievement). No prose is generated: components are either sourced directly
from the canonical profile or left unset for a future LLM layer to fill.
"""

from __future__ import annotations

from typing import Any, Sequence

from .domain import (
    EvidenceCitation,
    InterviewQuestion,
    SuggestedAnswer,
)
from .templates import QuestionTemplate


class QuestionBuilder:
    """Instantiate deterministic questions and structured answer outlines."""

    @staticmethod
    def render(pattern: str, values: dict[str, str]) -> str:
        """Substitute ``{placeholder}`` tokens with the provided values."""
        text = pattern
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text

    def build_question(
        self,
        template: QuestionTemplate,
        *,
        values: dict[str, str],
        evidence_citations: Sequence[EvidenceCitation],
        competency_ids: Sequence[str] = (),
        motivation: str | None = None,
        question_id: str,
    ) -> InterviewQuestion:
        text = self.render(template.prompt_pattern, values)
        return InterviewQuestion(
            id=question_id,
            category=template.category,
            text=text,
            competency_ids=tuple(competency_ids),
            context_refs=tuple(citation.source_ref() for citation in evidence_citations),
            evidence_citations=tuple(evidence_citations),
            difficulty=template.difficulty,
            motivation=motivation,
            template_id=template.template_id,
            suggested_answer=self.build_outline(
                evidence_citations=evidence_citations, values=values
            ),
        )

    def build_outline(
        self,
        *,
        evidence_citations: Sequence[EvidenceCitation],
        values: dict[str, str],
    ) -> SuggestedAnswer | None:
        """Build a structured outline from the bound profile excerpts.

        Each component is deterministically sourced from ``values`` when
        available; a component left unset means the profile does not contain it
        (the future LLM layer must not fabricate it).
        """
        evidence = tuple(evidence_citations)
        return SuggestedAnswer(
            situation=values.get("situation"),
            task=values.get("task"),
            action=values.get("action"),
            result=values.get("result"),
            evidence=evidence,
            achievement=values.get("achievement"),
        )
