"""Markdown cover letter generator with deterministic JD-aware tailoring."""

from __future__ import annotations

from ..exceptions import ValidationError
from ..export_contract import ExportContract, ExportSource
from ..optimizer import CVOptimizer
from .markdown_cv import MarkdownCVGenerator


class MarkdownCoverLetterGenerator:
    """Generate a Markdown cover letter from an export contract.

    When the contract carries a ``job_description``, the letter is
    deterministically tailored:
    - Requirements are extracted from the JD via ``CVOptimizer``.
    - Evidence sources are scored and reordered by JD relevance.
    - The opening paragraph references the top matched requirements.
    - The closing paragraph references the role and fit.

    When no JD is supplied the original generic logic is preserved
    (backward compatible).
    """

    supported_artifact_types = {"COVER_LETTER", "INTEREST_LETTER"}

    def __init__(self) -> None:
        """Create a cover letter generator using shared Markdown CV helpers."""
        self._markdown_cv = MarkdownCVGenerator()

    def generate(self, contract: ExportContract) -> str:
        """Generate Markdown using only the provided export contract."""
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for Markdown cover letter: {contract.artifact_type}"
            )

        name = self._markdown_cv._person_name(contract.person)
        default_title = "Interest Letter" if "interest" in contract.artifact_type.lower() else "Cover Letter"
        title = contract.artifact.get("title") or default_title
        context = contract.target_contexts[0] if contract.target_contexts else {}
        role = context.get("role")
        audience = context.get("audience") or "Hiring Team"

        jd = contract.job_description
        requirements = self._extract_requirements(jd) if jd else []
        has_jd = bool(requirements)

        lines = [
            f"# {title}",
            "",
            f"Dear {audience},",
            "",
            self._opening_paragraph(name, role, requirements),
            "",
        ]

        summary = self._first_source(contract.sources, {"professional_summary", "professionalsummary"})
        if summary:
            lines.extend([self._summary_text(summary), ""])

        evidence_items = self._evidence_items(contract.sources, requirements)
        if evidence_items:
            lines.extend(["## Relevant Evidence", *evidence_items, ""])

        lines.extend(
            [
                self._closing_paragraph(name, role, contract.reasoning, requirements) if has_jd else "Sincerely,",
                "",
                name,
            ]
        )
        return "\n".join(lines).strip() + "\n"

    # ------------------------------------------------------------------
    # JD requirement extraction (delegates to CVOptimizer)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_requirements(job_description: str) -> list[str]:
        """Extract normalised requirement tokens from a job description.

        Delegates to the well-tested ``CVOptimizer._extract_requirements``
        static method.  Returns a deduplicated, sorted list of lower-cased
        requirement strings.
        """
        return CVOptimizer._extract_requirements(job_description)

    # ------------------------------------------------------------------
    # Open / close paragraphs
    # ------------------------------------------------------------------

    @staticmethod
    def _opening_paragraph(name: str, role: object, requirements: list[str]) -> str:
        """Render the deterministic opening paragraph.

        When requirements are available the top 2–3 are referenced to
        demonstrate alignment.  Falls back to the generic opening when
        no role or requirements exist.
        """
        if role and requirements:
            top = requirements[:3]
            if len(top) == 1:
                req_text = top[0]
            elif len(top) == 2:
                req_text = f"{top[0]} and {top[1]}"
            else:
                req_text = f"{top[0]}, {top[1]}, and {top[2]}"
            return (
                f"I am writing to express strong interest in the {role} opportunity. "
                f"My background aligns closely with key requirements for this role, "
                f"including {req_text}. "
                f"The detailed evidence below is derived from verified profile sources."
            )
        if role:
            return (
                f"I am writing to express interest in the {role} opportunity. "
                f"My background is summarized below from verified profile sources."
            )
        return (
            f"I am writing to share {name}'s background for your consideration. "
            f"The summary below is derived from verified profile sources."
        )

    @staticmethod
    def _closing_paragraph(
        name: str,
        role: object,
        reasoning,
        requirements: list[str],
    ) -> str:
        """Render a JD-aware closing paragraph.

        References the role and, when reasoning findings are available,
        a career-stage or core-competency insight to reinforce fit.
        """
        base = "Sincerely"
        if not role:
            return f"{base},"

        parts = [f"I am confident that my experience in {role}"]
        if reasoning is not None:
            if reasoning.core_competencies:
                sample = reasoning.core_competencies[:2]
                parts.append(
                    f"particularly in {' and '.join(sample)}"
                )
            elif reasoning.career_stage:
                parts.append(
                    f"as a {reasoning.career_stage} professional"
                )
        parts.append(
            "would bring immediate value to your team. "
            "I welcome the opportunity to discuss my candidacy further."
        )
        return " ".join(parts) + f"\n\n{base},"

    # ------------------------------------------------------------------
    # Source helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_source(sources: list[ExportSource], source_types: set[str]) -> ExportSource | None:
        """Return the first source matching one of the given types."""
        for source in sources:
            if source.type.lower() in source_types:
                return source
        return None

    @staticmethod
    def _summary_text(source: ExportSource) -> str:
        """Render a professional summary source as prose."""
        return str(source.data.get("text") or source.data.get("label") or source.id)

    # ------------------------------------------------------------------
    # JD-aware evidence scoring & rendering
    # ------------------------------------------------------------------

    def _evidence_items(self, sources: list[ExportSource], requirements: list[str]) -> list[str]:
        """Render non-summary sources as evidence bullets, JD-ordered.

        When ``requirements`` is non-empty each source is scored by how
        many requirements its text fields contain; sources are returned
        highest-score-first.  Without requirements the original source
        order is preserved.
        """
        candidates: list[tuple[int, int, str]] = []
        for source in sources:
            if source.type.lower() in {"professional_summary", "professionalsummary"}:
                continue
            rendered = self._render_source(source)
            if not rendered:
                continue
            score = self._source_jd_score(source, requirements) if requirements else 0
            candidates.append((score, len(candidates), rendered))

        if requirements:
            candidates.sort(key=lambda t: (-t[0], t[1]))
        return [r for _, _, r in candidates]

    def _source_jd_score(self, source: ExportSource, requirements: list[str]) -> int:
        """Count how many JD requirement tokens appear in a source's text.

        Checks the most descriptive fields of each source type.
        """
        data = source.data
        text = ""
        st = source.type.lower()
        if st == "experience":
            text = " ".join(
                str(v) for v in [data.get("title"), data.get("scope"), data.get("organization")] if v
            )
        elif st == "project":
            text = " ".join(
                str(v) for v in [data.get("name"), data.get("description")] if v
            )
        elif st == "skill":
            text = " ".join(
                str(v) for v in [data.get("name"), data.get("description"), data.get("category")] if v
            )
        elif st == "achievement":
            text = str(data.get("statement") or "")
        elif st == "certification":
            text = str(data.get("name") or "")
        elif st == "education":
            text = " ".join(
                str(v) for v in [data.get("program"), data.get("fieldOfStudy"), data.get("institution")] if v
            )
        text_lower = text.lower()
        return sum(1 for req in requirements if req in text_lower)

    # ------------------------------------------------------------------
    # Source rendering
    # ------------------------------------------------------------------

    def _render_source(self, source: ExportSource) -> str:
        """Render a source as a cover-letter evidence bullet."""
        data = source.data
        source_type = source.type.lower()
        if source_type == "experience":
            title = data.get("title") or source.id
            scope = data.get("scope")
            return f"- {title}: {scope}" if scope else f"- {title}"
        if source_type == "project":
            name = data.get("name") or source.id
            description = data.get("description")
            return f"- {name}: {description}" if description else f"- {name}"
        if source_type == "skill":
            name = data.get("name") or source.id
            description = data.get("description")
            return f"- {name}: {description}" if description else f"- {name}"
        if source_type == "achievement":
            return f"- {data.get('statement') or source.id}"
        if source_type == "certification":
            return f"- {data.get('name') or source.id}"
        if source_type == "education":
            label = self._markdown_cv._education_label(data, source.id)
            return f"- {label}"
        return ""
