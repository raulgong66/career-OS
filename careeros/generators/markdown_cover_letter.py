"""Markdown cover letter generator."""

from __future__ import annotations

from ..exceptions import ValidationError
from ..export_contract import ExportContract, ExportSource
from .markdown_cv import MarkdownCVGenerator


class MarkdownCoverLetterGenerator:
    """Generate a minimal Markdown cover letter from an export contract."""

    supported_artifact_types = {"COVER_LETTER"}

    def __init__(self) -> None:
        """Create a cover letter generator using shared Markdown CV helpers."""
        self._markdown_cv = MarkdownCVGenerator()

    def generate(self, contract: ExportContract) -> str:
        """Generate Markdown using only the provided export contract."""
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(f"Unsupported artifact type for Markdown cover letter: {contract.artifact_type}")

        name = self._markdown_cv._person_name(contract.person)
        title = contract.artifact.get("title") or "Cover Letter"
        context = contract.target_contexts[0] if contract.target_contexts else {}
        role = context.get("role")
        audience = context.get("audience") or "Hiring Team"

        lines = [
            f"# {title}",
            "",
            f"Dear {audience},",
            "",
            self._opening_paragraph(name, role),
            "",
        ]

        summary = self._first_source(contract.sources, {"professional_summary", "professionalsummary"})
        if summary:
            lines.extend([self._summary_text(summary), ""])

        evidence_items = self._evidence_items(contract.sources)
        if evidence_items:
            lines.extend(["## Relevant Evidence", *evidence_items, ""])

        lines.extend(
            [
                "Sincerely,",
                "",
                name,
                "",
                f"_Derived from profile version: {contract.profile_version}_",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _opening_paragraph(name: str, role: object) -> str:
        """Render the deterministic opening paragraph."""
        if role:
            return f"I am writing to express interest in the {role} opportunity. My background is summarized below from verified profile sources."
        return f"I am writing to share {name}'s background for your consideration. The summary below is derived from verified profile sources."

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

    def _evidence_items(self, sources: list[ExportSource]) -> list[str]:
        """Render non-summary sources as concise evidence bullets."""
        items = []
        for source in sources:
            if source.type.lower() in {"professional_summary", "professionalsummary"}:
                continue
            rendered = self._render_source(source)
            if rendered:
                items.append(rendered)
        return items

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
