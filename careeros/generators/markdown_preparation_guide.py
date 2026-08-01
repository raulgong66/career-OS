"""Markdown Interview Preparation Guide generator (M1.16).

Renders a deterministic, evidence-backed ``InterviewPreparationGuide`` as a
professional Markdown document. The generator is a pure consumer of the
``ExportContract`` — it reads ``interview_plan`` attached by the generation
pipeline and renders every section from the plan's deterministic data. Internal
ids, ``evidenceRefs`` and ``contextRefs`` are never exposed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import ValidationError
from ..export_contract import ExportContract
from .markdown_cv import MarkdownCVGenerator

if TYPE_CHECKING:
    from ..interview.domain import InterviewPlan, SuggestedAnswer

_SECTION_TITLES: dict[str, str] = {
    "technical": "Technical Questions",
    "behavioral": "Behavioral Questions",
    "leadership": "Leadership Questions",
    "project_deep_dive": "Project Deep Dive",
    "problem_solving": "Problem Solving",
    "career_motivation": "Career Motivation",
}

_STAR_LABELS: dict[str, str] = {
    "technical": "Technical",
    "behavioral": "Behavioral",
    "leadership": "Leadership",
    "project_deep_dive": "Project Deep Dive",
    "problem_solving": "Problem Solving",
    "career_motivation": "Career Motivation",
}

_EVIDENCE_TYPE_LABELS: dict[str, str] = {
    "skill": "Skills",
    "experience": "Experiences",
    "project": "Projects",
    "achievement": "Achievements",
    "education": "Education",
    "certification": "Certifications",
    "professional_summary": "Professional summary",
    "professionalsummary": "Professional summary",
    "person": "Profile positioning",
}


class MarkdownPreparationGuideGenerator:
    """Render a deterministic, evidence-backed Interview Preparation Guide.

    Every section is driven by ``InterviewPlan`` data attached to the
    contract.  Internal ids, evidence-refs and context-refs are never
    exposed — only verbatim profile excerpts (quotes) are rendered as
    human-readable references.
    """

    supported_artifact_types = {"INTERVIEW_PREPARATION_GUIDE"}

    def __init__(self) -> None:
        self._markdown_cv = MarkdownCVGenerator()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(self, contract: ExportContract) -> str:
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for Markdown preparation guide:"
                f" {contract.artifact_type}"
            )

        plan = contract.interview_plan
        if plan is None:
            raise ValidationError(
                "Interview preparation guide requires an interview_plan"
                " on the export contract"
            )

        lines: list[str] = []

        title = contract.artifact.get("title") or "Interview Preparation Guide"
        lines.append(f"# {title}")
        lines.append("")

        if plan.target_role:
            lines.append(f"**Target Role:** {plan.target_role}")
            lines.append("")

        summary = self._candidate_summary(contract)
        if summary:
            lines.append("## Candidate Summary")
            lines.append(summary)
            lines.append("")

        self._render_question_sections(lines, plan)
        self._render_star_outlines(lines, plan)
        self._render_preparation_checklist(lines, plan)
        self._render_evidence_notes(lines, plan)

        return "\n".join(lines).strip() + "\n"

    # ------------------------------------------------------------------
    # Candidate summary (reuses deterministic MarkdownCVGenerator helper)
    # ------------------------------------------------------------------

    def _candidate_summary(self, contract: ExportContract) -> str:
        """Build a deterministic summary from profile data without AI.

        Prefers reasoning findings (career stage, domain expertise,
        technology breadth) over raw profile fields.
        """
        summary = self._markdown_cv._render_summary(contract)
        if summary:
            return summary

        for source in contract.sources:
            if source.type.lower() in ("professional_summary", "professionalsummary"):
                text = source.data.get("text") or source.data.get("label", "")
                if text:
                    return str(text)

        person = contract.person
        headline = (person.get("positioning") or {}).get("headline")
        if headline:
            return str(headline)
        return ""

    # ------------------------------------------------------------------
    # Question sections (grouped by category, CATEGORY_ORDER)
    # ------------------------------------------------------------------

    def _render_question_sections(self, lines: list[str], plan: "InterviewPlan") -> None:
        grouped = plan.questions_by_category()
        for category_key, section_title in _SECTION_TITLES.items():
            questions = grouped.get(category_key, ())
            if not questions:
                continue
            lines.append(f"## {section_title}")
            for question in questions:
                lines.append(f"• {question.text}")
                answer = question.suggested_answer
                if answer is not None:
                    for label, value in self._answer_components(answer):
                        lines.append(f"- {label}: {value}")
                lines.append("")
            lines.append("")

    def _answer_components(self, answer: "SuggestedAnswer") -> list[tuple[str, str]]:
        """Ordered, non-empty components of a suggested answer."""
        components: list[tuple[str, str]] = []
        evidence_text = self._evidence_text(answer)
        for label, value in (
            ("Situation", answer.situation),
            ("Task", answer.task),
            ("Action", answer.action),
            ("Result", answer.result),
            ("Evidence", evidence_text or None),
            ("Achievement", answer.achievement),
        ):
            if value:
                components.append((label, str(value)))
        return components

    @staticmethod
    def _evidence_text(answer: "SuggestedAnswer") -> str:
        quotes: list[str] = []
        for citation in answer.evidence:
            quote = citation.quote
            if quote:
                text = str(quote).strip()
                if text and text not in quotes:
                    quotes.append(text)
        return "; ".join(quotes)

    # ------------------------------------------------------------------
    # Suggested STAR outlines (consolidated practice recap)
    # ------------------------------------------------------------------

    def _render_star_outlines(self, lines: list[str], plan: "InterviewPlan") -> None:
        """Compact STAR skeleton per question for quick rehearsal."""
        outlines: list[str] = []
        grouped = plan.questions_by_category()
        for category_key, label in _STAR_LABELS.items():
            for index, question in enumerate(grouped.get(category_key, ()), start=1):
                answer = question.suggested_answer
                if answer is None:
                    continue
                skeleton = self._star_skeleton(answer)
                if skeleton:
                    outlines.append(f"- {label} {index}: {skeleton}")
        if not outlines:
            return
        lines.append("## Suggested STAR Outlines")
        lines.extend(outlines)
        lines.append("")

    @staticmethod
    def _star_skeleton(answer: "SuggestedAnswer") -> str:
        parts: list[str] = []
        for label, value in (
            ("Situation", answer.situation),
            ("Task", answer.task),
            ("Action", answer.action),
            ("Result", answer.result),
            ("Achievement", answer.achievement),
        ):
            if value:
                parts.append(f"{label}: {value}")
        return "; ".join(parts)

    # ------------------------------------------------------------------
    # Preparation checklist (deterministic, data-aware template)
    # ------------------------------------------------------------------

    def _render_preparation_checklist(
        self, lines: list[str], plan: "InterviewPlan"
    ) -> None:
        items: list[str] = []
        if plan.target_role:
            items.append(f"- Focus your preparation on the {plan.target_role} role.")
        items.append(
            f"- Review all {plan.question_count} questions and rehearse concise,"
            f" structured answers."
        )
        items.append(
            "- Use the STAR format (Situation, Task, Action, Result) to"
            " structure your answers."
        )
        if plan.competencies:
            items.append(
                f"- Refresh the {len(plan.competencies)} core competencies"
                f" highlighted in this guide."
            )
        has_evidence = any(
            q.suggested_answer is not None and q.suggested_answer.evidence
            for q in plan.questions
        )
        if has_evidence:
            items.append(
                "- Practice citing the evidence in your suggested answers."
            )
        if plan.target_role_requirements:
            items.append(
                "- Map each prepared answer to the target role's key requirements."
            )
        lines.append("## Preparation Checklist")
        lines.extend(items)
        lines.append("")

    # ------------------------------------------------------------------
    # Evidence notes (human-readable, no internal ids)
    # ------------------------------------------------------------------

    def _render_evidence_notes(
        self, lines: list[str], plan: "InterviewPlan"
    ) -> None:
        by_type: dict[str, list[str]] = {}
        for question in plan.questions:
            citations = (
                question.suggested_answer.evidence
                if question.suggested_answer is not None
                else question.evidence_citations
            )
            for citation in citations:
                quote = citation.quote
                if not quote:
                    continue
                label = _EVIDENCE_TYPE_LABELS.get(
                    citation.element_type.lower(), citation.element_type
                )
                bucket = by_type.setdefault(label, [])
                text = str(quote).strip()
                if text and text not in bucket:
                    bucket.append(text)
        if not by_type:
            return
        lines.append("## Evidence Notes")
        lines.append(
            "This guide grounds its questions in the following profile evidence:"
        )
        for label in _EVIDENCE_TYPE_LABELS.values():
            bucket = by_type.pop(label, None)
            if bucket:
                lines.append(f"- {label}: {'; '.join(bucket)}")
        for label in sorted(by_type):  # any remaining unlabelled element types
            bucket = by_type[label]
            lines.append(f"- {label}: {'; '.join(bucket)}")
        lines.append("")