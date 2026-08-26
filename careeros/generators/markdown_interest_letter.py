"""Markdown interest letter generator with deterministic JD-aware tailoring.

Unlike the cover letter generator, this produces a requirement-centric letter
that connects JD requirements to specific profile evidence, rather than
listing all profile sources as bullets.
"""

from __future__ import annotations

from ..exceptions import ValidationError
from ..export_contract import ExportContract, ExportSource
from ..optimizer import CVOptimizer
from .markdown_cv import MarkdownCVGenerator
from .source_utils import extract_source_text

_ACRONYMS: set[str] = {
    "cissp", "siem", "aws", "gcp", "sql", "devops", "devsecops",
    "mlops", "gitops", "ci/cd", "iam", "iac", "sre", "nlp", "cv",
    "ml", "dl", "llm", "soar", "vpn", "mdm",
}


class MarkdownInterestLetterGenerator:
    """Generate a personalized interest letter from an export contract.

    The generator is requirement-centric: it scores profile evidence against
    JD requirements, selects the strongest matches, groups them by
    requirement, and renders each group as a coherent prose paragraph
    connecting the requirement to concrete candidate experience.
    """

    supported_artifact_types = {"INTEREST_LETTER"}
    _MAX_EVIDENCE = 5
    _MAX_BODY_PARAGRAPHS = 4

    def __init__(self) -> None:
        self._markdown_cv = MarkdownCVGenerator()

    def generate(self, contract: ExportContract) -> str:
        """Generate a personalized Markdown interest letter."""
        if contract.artifact_type.upper() not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for interest letter: {contract.artifact_type}"
            )

        name = self._person_name(contract.person)
        title = contract.artifact.get("title") or "Interest Letter"
        context = contract.target_contexts[0] if contract.target_contexts else {}
        role = context.get("role")
        audience = context.get("audience") or "Hiring Team"

        jd = contract.job_description
        requirements = CVOptimizer.extract_requirements(jd) if jd else []

        if requirements:
            scored = self._score_sources(contract.sources, requirements)
            evidence = scored[: self._MAX_EVIDENCE]
            requirement_groups = self._group_by_requirement(evidence)
        else:
            evidence = [
                s for s in contract.sources
                if s.type.lower() not in {"professional_summary", "professionalsummary"}
            ][: self._MAX_EVIDENCE]
            requirement_groups = []

        lines = [f"# {title}", "", f"Dear {audience},", ""]

        lines.append(self._opening_paragraph(role, requirement_groups))
        lines.append("")

        summary = self._first_source(
            contract.sources, {"professional_summary", "professionalsummary"}
        )
        if summary:
            lines.append(self._summary_text(summary))
            lines.append("")

        for para in self._body_paragraphs(evidence, requirement_groups):
            lines.append(para)
            lines.append("")

        lines.append(self._closing_paragraph(name, role, requirement_groups))
        lines.append("")
        lines.append(name)

        return "\n".join(lines).strip() + "\n"

    # ------------------------------------------------------------------
    # Source scoring
    # ------------------------------------------------------------------

    def _score_sources(
        self, sources: list[ExportSource], requirements: list[str]
    ) -> list[tuple[ExportSource, int, list[str]]]:
        """Score non-summary sources against JD requirements.

        Returns ``(source, score, matched_requirements)`` tuples for
        sources with at least one match, sorted highest-score-first.
        """
        if not requirements:
            return []

        scored: list[tuple[ExportSource, int, list[str]]] = []
        for source in sources:
            if source.type.lower() in {"professional_summary", "professionalsummary"}:
                continue
            text = extract_source_text(source).lower()
            matched = [r for r in requirements if r in text]
            if matched:
                scored.append((source, len(matched), matched))

        scored.sort(key=lambda x: -x[1])
        return scored

    @staticmethod
    def _group_by_requirement(
        evidence: list[tuple[ExportSource, int, list[str]]],
    ) -> list[tuple[str, list[ExportSource]]]:
        """Group evidence by the requirements they demonstrate.

        Returns ``(requirement, [sources])`` sorted by source count
        descending so the most-evidenced requirements appear first.
        """
        groups: dict[str, list[ExportSource]] = {}
        for source, _score, matched_reqs in evidence:
            for req in matched_reqs:
                groups.setdefault(req, []).append(source)
        return sorted(groups.items(), key=lambda x: -len(x[1]))

    # ------------------------------------------------------------------
    # Letter sections
    # ------------------------------------------------------------------

    def _opening_paragraph(
        self, role: object, requirement_groups: list[tuple[str, list[ExportSource]]]
    ) -> str:
        """Build opening paragraph referencing top requirements."""
        top_reqs = [
            self._display_requirement(req) for req, _ in requirement_groups[:3]
        ]

        if role and top_reqs:
            req_text = self._join_requirements(top_reqs)
            return (
                f"I am writing to express strong interest in the {role} opportunity. "
                f"My background aligns closely with your requirements in {req_text}."
            )
        if role:
            return (
                f"I am writing to express interest in the {role} opportunity. "
                f"I believe my experience is well suited to this role."
            )
        return (
            "I am writing to express interest in this opportunity. "
            "I believe my experience is well suited to this role."
        )

    def _body_paragraphs(
        self, evidence: list[ExportSource], requirement_groups: list[tuple[str, list[ExportSource]]]
    ) -> list[str]:
        """Build body paragraphs connecting requirements to evidence.

        When requirement groups exist (JD provided), each paragraph
        connects one requirement to matching evidence. When no JD is
        provided, each evidence item is rendered as its own paragraph.
        """
        paragraphs: list[str] = []
        if requirement_groups:
            for req, sources in requirement_groups[: self._MAX_BODY_PARAGRAPHS]:
                para = self._requirement_paragraph(req, sources)
                if para:
                    paragraphs.append(para)
        else:
            for source in evidence[: self._MAX_BODY_PARAGRAPHS]:
                desc = self._source_prose(source)
                if desc:
                    paragraphs.append(f"{self._lower_first(desc)}.")
        return paragraphs

    def _requirement_paragraph(
        self, requirement: str, sources: list[ExportSource]
    ) -> str:
        """Build a paragraph connecting one requirement to evidence."""
        display_req = self._display_requirement(requirement)

        evidence_parts: list[str] = []
        for source in sources[:2]:
            desc = self._source_prose(source)
            if desc:
                evidence_parts.append(desc)

        if not evidence_parts:
            return ""

        evidence_text = " and ".join(evidence_parts)
        return f"Regarding {display_req}, {evidence_text}."

    def _closing_paragraph(
        self,
        name: str,
        role: object,
        requirement_groups: list[tuple[str, list[ExportSource]]],
    ) -> str:
        """Build closing paragraph referencing role and strongest competency."""
        if not role:
            return "Sincerely,"

        strongest = ""
        if requirement_groups:
            strongest = self._display_requirement(requirement_groups[0][0])

        if strongest:
            return (
                f"I am confident that my experience in {role}, "
                f"particularly in {strongest}, "
                f"would bring immediate value to your team. "
                f"I welcome the opportunity to discuss my candidacy further.\n\nSincerely,"
            )
        return (
            f"I am confident that my experience in {role} "
            f"would bring immediate value to your team. "
            f"I welcome the opportunity to discuss my candidacy further.\n\nSincerely,"
        )

    # ------------------------------------------------------------------
    # Source prose rendering
    # ------------------------------------------------------------------

    def _source_prose(self, source: ExportSource) -> str:
        """Render a source as a natural prose fragment."""
        data = source.data
        st = source.type.lower()

        if st == "experience":
            title = data.get("title", source.id)
            scope = data.get("scope")
            if scope:
                return f"my experience as {title}: {self._first_clause(scope)}"
            return f"my experience as {title}"

        if st == "skill":
            name = data.get("name", source.id)
            desc = data.get("description")
            if desc:
                return f"my expertise in {name}, including {self._lower_first(desc)}"
            return f"my expertise in {name}"

        if st == "certification":
            name = data.get("name", source.id)
            return f"my {name} certification"

        if st == "project":
            name = data.get("name", source.id)
            desc = data.get("description")
            if desc:
                return f"my project {name}: {self._first_clause(desc)}"
            return f"my project {name}"

        if st == "achievement":
            stmt = data.get("statement", "")
            return self._lower_first(stmt) if stmt else ""

        if st == "education":
            program = data.get("program", source.id)
            institution = data.get("institution")
            if institution:
                return f"my {program} from {institution}"
            return f"my {program} education"

        return ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _person_name(self, person: dict) -> str:
        return self._markdown_cv._person_name(person)

    @staticmethod
    def _first_source(
        sources: list[ExportSource], source_types: set[str]
    ) -> ExportSource | None:
        for source in sources:
            if source.type.lower() in source_types:
                return source
        return None

    @staticmethod
    def _summary_text(source: ExportSource) -> str:
        return str(source.data.get("text") or source.data.get("label") or source.id)

    @staticmethod
    def _display_requirement(token: str) -> str:
        """Convert a normalised requirement token to a human-readable name."""
        if token in _ACRONYMS:
            return token.upper()
        if "/" in token:
            return "/".join(
                p.upper() if p in _ACRONYMS else p.title() for p in token.split("/")
            )
        return token.title()

    @staticmethod
    def _join_requirements(reqs: list[str]) -> str:
        if len(reqs) == 1:
            return reqs[0]
        if len(reqs) == 2:
            return f"{reqs[0]} and {reqs[1]}"
        return f"{reqs[0]}, {reqs[1]}, and {reqs[2]}"

    @staticmethod
    def _lower_first(text: str) -> str:
        """Lowercase the first character when it looks like a regular word."""
        if not text:
            return ""
        if text[0].isupper() and (len(text) < 2 or text[1].islower()):
            return text[0].lower() + text[1:]
        return text

    @staticmethod
    def _first_clause(text: str) -> str:
        """Return the first clause of a semicolon-separated string."""
        parts = [p.strip() for p in text.split(";") if p.strip()]
        return parts[0] if parts else text
