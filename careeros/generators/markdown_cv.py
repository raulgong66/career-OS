"""Markdown CV generator."""

from __future__ import annotations

from typing import Any

from ..exceptions import ValidationError
from ..export_contract import ExportContract, ExportSource


class MarkdownCVGenerator:
    """Generate a minimal Markdown CV from an export contract."""

    supported_artifact_types = {"CV", "RESUME"}

    def generate(self, contract: ExportContract) -> str:
        """Generate Markdown using the provided export contract.

        When reasoning findings are present on the contract, deterministic
        insights (strongest skills, core competencies, career stage, etc.)
        are included in the output.
        """
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(f"Unsupported artifact type for Markdown CV: {contract.artifact_type}")

        lines: list[str] = []
        lines.extend(self._render_header(contract))
        lines.extend(self._render_target_context(contract))
        lines.extend(self._render_reasoning(contract))

        grouped = self._group_sources(contract.sources)
        sections = [
            ("Professional Summary", grouped.get("professional_summary", [])),
            ("Experience", grouped.get("experience", [])),
            ("Projects", grouped.get("project", [])),
            ("Skills", grouped.get("skill", [])),
            ("Achievements", grouped.get("achievement", [])),
            ("Education", grouped.get("education", [])),
            ("Certifications", grouped.get("certification", [])),
        ]

        for title, sources in sections:
            rendered = self._render_section(title, sources)
            if rendered:
                lines.extend(rendered)

        lines.append(f"_Derived from profile version: {contract.profile_version}_")
        return "\n".join(lines).strip() + "\n"

    def _render_reasoning(self, contract: ExportContract) -> list[str]:
        """Render reasoning-derived sections when findings are available."""
        r = contract.reasoning
        if r is None:
            return []

        lines: list[str] = []

        if r.career_stage:
            lines.append(f"**Career Stage:** {r.career_stage}")

        if r.core_competencies:
            items = ", ".join(r.core_competencies)
            lines.append(f"**Core Competencies:** {items}")

        if r.technology_breadth:
            items = ", ".join(r.technology_breadth)
            lines.append(f"**Technology Breadth:** {items}")

        if r.strongest_skills:
            items = ", ".join(r.strongest_skills)
            lines.append(f"**Strongest Skills:** {items}")

        if r.strongest_experience:
            title = r.strongest_experience.get("title") or r.strongest_experience.get("role", "")
            org = r.strongest_experience.get("organization") or r.strongest_experience.get("employer", "")
            if title:
                parts = [f"**Strongest Experience:** {title}"]
                if org:
                    parts.append(f"at {org}")
                lines.append(" ".join(parts))

        if r.career_highlights:
            highlights = []
            for h in r.career_highlights:
                text = h.get("highlight") or h.get("title") or h.get("summary", "")
                if text:
                    highlights.append(str(text))
            if highlights:
                lines.append("**Career Highlights:** " + "; ".join(highlights))

        if lines:
            lines.insert(0, "")
            lines.append("")

        return lines

    def _render_header(self, contract: ExportContract) -> list[str]:
        """Render the CV heading from person and artifact data."""
        person = contract.person
        name = self._person_name(person)
        headline = person.get("positioning", {}).get("headline")
        title = contract.artifact.get("title")

        lines = [f"# {name}"]
        if headline:
            lines.append(str(headline))
        if title:
            lines.extend(["", f"**Artifact:** {title}"])
        lines.append("")
        return lines

    def _render_target_context(self, contract: ExportContract) -> list[str]:
        """Render target context metadata when present."""
        if not contract.target_contexts:
            return []

        context = contract.target_contexts[0]
        parts = [
            value
            for value in [
                context.get("role"),
                context.get("market"),
                context.get("geography"),
                context.get("language"),
            ]
            if value
        ]
        if not parts:
            return []
        return ["## Target Context", ", ".join(str(part) for part in parts), ""]

    def _render_section(self, title: str, sources: list[ExportSource]) -> list[str]:
        """Render a Markdown section for resolved sources."""
        items = [self._render_source(source) for source in sources]
        items = [item for item in items if item]
        if not items:
            return []
        return [f"## {title}", *items, ""]

    def _render_source(self, source: ExportSource) -> str:
        """Render a source as a Markdown bullet."""
        data = source.data
        source_type = source.type.lower()
        if source_type in {"professional_summary", "professionalsummary"}:
            text = data.get("text") or data.get("label") or source.id
            return f"- {text}"
        if source_type == "experience":
            title = data.get("title") or source.id
            date_range = self._date_range(data.get("dateRange", {}))
            scope = data.get("scope")
            suffix = f" ({date_range})" if date_range else ""
            detail = f": {scope}" if scope else ""
            return f"- **{title}**{suffix}{detail}"
        if source_type == "project":
            name = data.get("name") or source.id
            description = data.get("description")
            return f"- **{name}**: {description}" if description else f"- **{name}**"
        if source_type == "skill":
            name = data.get("name") or source.id
            category = data.get("category")
            return f"- {name} ({category})" if category else f"- {name}"
        if source_type == "achievement":
            return f"- {data.get('statement') or source.id}"
        if source_type == "education":
            label = self._education_label(data, source.id)
            date_range = self._date_range(data.get("dateRange", {}))
            return f"- {label} ({date_range})" if date_range else f"- {label}"
        if source_type == "certification":
            name = data.get("name") or source.id
            credential_id = data.get("credentialId")
            return f"- {name} (Credential ID: {credential_id})" if credential_id else f"- {name}"
        return ""

    @staticmethod
    def _group_sources(sources: list[ExportSource]) -> dict[str, list[ExportSource]]:
        """Group sources by normalized source type while preserving order."""
        grouped: dict[str, list[ExportSource]] = {}
        for source in sources:
            key = source.type.lower()
            if key == "professionalsummary":
                key = "professional_summary"
            grouped.setdefault(key, []).append(source)
        return grouped

    @staticmethod
    def _person_name(person: dict[str, Any]) -> str:
        """Return the best available professional name."""
        for name in person.get("names", []):
            if name.get("usage") == "professional" and name.get("value"):
                return str(name["value"])
        for name in person.get("names", []):
            if name.get("value"):
                return str(name["value"])
        return str(person.get("id", "Unnamed Profile"))

    @staticmethod
    def _date_range(date_range: dict[str, Any]) -> str:
        """Render a compact date range."""
        if not isinstance(date_range, dict):
            return ""
        if date_range.get("label"):
            return str(date_range["label"])
        start = date_range.get("start")
        end = date_range.get("end")
        if start and end:
            return f"{start} - {end}"
        return str(start or end or "")

    @staticmethod
    def _education_label(data: dict[str, Any], fallback: str) -> str:
        """Render an education entry label."""
        program = data.get("program")
        field = data.get("fieldOfStudy")
        if program and field:
            return f"{program} in {field}"
        return str(program or field or fallback)
