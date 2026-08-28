"""Markdown interest letter generator with deterministic JD-aware tailoring.

Unlike the cover letter generator, this produces a requirement-centric letter
that connects JD requirements to specific profile evidence, rather than
listing all profile sources as bullets.
"""

from __future__ import annotations

import re

from ..exceptions import ValidationError
from ..export_contract import ExportContract, ExportSource
from ..optimizer import CVOptimizer, _REQUIREMENT_ALIASES
from ..reporting.partner_output import jd_role_text
from .markdown_cv import MarkdownCVGenerator
from .source_utils import extract_source_text

# Reverse of _REQUIREMENT_ALIASES: canonical form → original aliases.
# Used by _score_sources to match "AWS" in source text when the requirement
# has been normalised to "amazon web services".
_REVERSE_REQ_ALIASES: dict[str, list[str]] = {}
for _alias, _canonical in _REQUIREMENT_ALIASES.items():
    _REVERSE_REQ_ALIASES.setdefault(_canonical, []).append(_alias)

_ACronyms: set[str] = {
    "cissp", "siem", "aws", "gcp", "sql", "devops", "devsecops",
    "mlops", "gitops", "ci/cd", "iam", "iac", "sre", "nlp", "cv",
    "ml", "dl", "llm", "soar", "vpn", "mdm",
}

# ---------------------------------------------------------------------------
# Requirement consolidation
# ---------------------------------------------------------------------------
# Maps raw extracted tokens to canonical theme keys so that semantically
# overlapping requirements (e.g. "google" + "google cloud") are merged into
# a single paragraph instead of appearing as separate requirement groups.

_CONSOLIDATION_ALIASES: dict[str, str] = {
    # Cloud / infrastructure
    "aws": "cloud_infra",
    "amazon web services": "cloud_infra",
    "cloud": "cloud_infra",
    "gcp": "cloud_infra",
    "google cloud": "cloud_infra",
    "google cloud platform": "cloud_infra",
    "azure": "cloud_infra",
    "cloud infrastructure": "cloud_infra",
    "cloud platforms": "cloud_infra",
    "cloud security": "cloud_infra",
    "cloud architecture": "cloud_infra",
    "cloud computing": "cloud_infra",
    "cloud services": "cloud_infra",
    "cloud native": "cloud_infra",
    "cloud migration": "cloud_infra",
    "cloud management": "cloud_infra",
    # Google (standalone or with cloud — both map to cloud_infra)
    "google": "cloud_infra",
    # Security / DevSecOps
    "devsecops": "security_devops",
    "devops": "security_devops",
    "cybersecurity": "security_devops",
    "security": "security_devops",
    "infosec": "security_devops",
    "information security": "security_devops",
    "identity and access management": "security_devops",
    "threat detection": "security_devops",
    "incident response": "security_devops",
    "threat hunting": "security_devops",
    "sre": "security_devops",
    "site reliability engineering": "security_devops",
    "siem": "security_devops",
    "soar": "security_devops",
    "observability": "infra_tooling",
    # Programming / software engineering
    "python": "software_eng",
    "java": "software_eng",
    "javascript": "software_eng",
    "typescript": "software_eng",
    "golang": "software_eng",
    "go": "software_eng",
    "rust": "software_eng",
    "c++": "software_eng",
    "c#": "software_eng",
    ".net": "software_eng",
    "node.js": "software_eng",
    "nodejs": "software_eng",
    "react": "software_eng",
    "vue": "software_eng",
    "angular": "software_eng",
    "frontend": "software_eng",
    "backend": "software_eng",
    "fullstack": "software_eng",
    "full stack": "software_eng",
    "full-stack": "software_eng",
    "microservices": "software_eng",
    "api": "software_eng",
    "rest api": "software_eng",
    "restful": "software_eng",
    # ML / AI / data
    "machine learning": "ml_ai",
    "deep learning": "ml_ai",
    "nlp": "ml_ai",
    "natural language processing": "ml_ai",
    "computer vision": "ml_ai",
    "mlops": "ml_ai",
    "machine learning operations": "ml_ai",
    "data science": "ml_ai",
    "ai": "ml_ai",
    "artificial intelligence": "ml_ai",
    "tensorflow": "ml_ai",
    "pytorch": "ml_ai",
    "llm": "ml_ai",
    "large language models": "ml_ai",
    "cv": "ml_ai",
    # Infrastructure / DevOps tooling
    "kubernetes": "infra_tooling",
    "docker": "infra_tooling",
    "terraform": "infra_tooling",
    "ansible": "infra_tooling",
    "helm": "infra_tooling",
    "jenkins": "infra_tooling",
    "ci/cd": "infra_tooling",
    "cicd": "infra_tooling",
    "gitops": "infra_tooling",
    "iac": "infra_tooling",
    "infrastructure as code": "infra_tooling",
    "infrastructure": "infra_tooling",
    "linux": "infra_tooling",
    "git": "infra_tooling",
    # Databases / data
    "sql": "data_platform",
    "nosql": "data_platform",
    "postgresql": "data_platform",
    "mysql": "data_platform",
    "mongodb": "data_platform",
    "redis": "data_platform",
    "elasticsearch": "data_platform",
    "data engineering": "data_platform",
    "data pipeline": "data_platform",
    "etl": "data_platform",
    "data warehouse": "data_platform",
    # Soft skills / leadership
    "leadership": "leadership",
    "mentoring": "leadership",
    "agile": "leadership",
    "scrum": "leadership",
    "cross-functional": "leadership",
    "stakeholder management": "leadership",
    "communication": "leadership",
}

# Canonical theme → human-readable display label (for internal use only;
# not exposed as paragraph headings in the final output).
_THEME_LABELS: dict[str, str] = {
    "cloud_infra": "Cloud and Infrastructure",
    "security_devops": "Security and DevOps",
    "software_eng": "Software Engineering",
    "ml_ai": "Machine Learning and AI",
    "infra_tooling": "Infrastructure Tooling",
    "data_platform": "Data Platforms",
    "leadership": "Leadership",
}

# Preferred order when multiple themes are present — stronger / more
# discriminating themes appear earlier in the letter body.
_THEME_PRIORITY: list[str] = [
    "ml_ai",
    "cloud_infra",
    "security_devops",
    "software_eng",
    "data_platform",
    "infra_tooling",
    "leadership",
]


class MarkdownInterestLetterGenerator:
    """Generate a personalized interest letter from an export contract.

    The generator is requirement-centric: it scores profile evidence against
    JD requirements, selects the strongest matches, groups them by
    requirement, and renders each group as a coherent prose paragraph
    connecting the requirement to concrete candidate experience.
    """

    supported_artifact_types = {"INTEREST_LETTER"}
    _MAX_EVIDENCE = 5
    _MAX_BODY_PARAGRAPHS = 3

    def __init__(self) -> None:
        self._markdown_cv = MarkdownCVGenerator()

    @staticmethod
    def _resolve_role(
        contract: ExportContract, context: dict[str, Any]
    ) -> str:
        """Resolve the letter role with JD-first precedence.

        1. the role title extracted from the job description, when present
        2. the selected target-context role
        3. the profile positioning headline as a last resort

        A JD role only overrides the target-context role when the JD
        actually names one; generic JDs keep the curated target role.
        """
        if contract.job_description:
            jd_role = jd_role_text(contract.job_description)
            if jd_role:
                return jd_role
        target_role = context.get("role")
        if target_role:
            return str(target_role)
        headline = (contract.person.get("positioning") or {}).get("headline")
        if headline:
            return str(headline)
        return ""

    def generate(self, contract: ExportContract) -> str:
        """Generate a personalized Markdown interest letter."""
        if contract.artifact_type.upper() not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for interest letter: {contract.artifact_type}"
            )

        name = self._person_name(contract.person)
        title = contract.artifact.get("title") or "Interest Letter"
        context = contract.target_contexts[0] if contract.target_contexts else {}
        role = self._resolve_role(contract, context)
        audience = context.get("audience") or "Hiring Team"

        jd = contract.job_description
        requirements = CVOptimizer.extract_requirements(jd) if jd else []

        if requirements:
            scored = self._score_sources(contract.sources, requirements)
            evidence = scored[: self._MAX_EVIDENCE]
            theme_groups = self._assign_themes(evidence)
            label_groups = self._pooled_theme_groups(evidence)
        else:
            evidence = [
                s for s in contract.sources
                if s.type.lower() not in {"professional_summary", "professionalsummary"}
            ][: self._MAX_EVIDENCE]
            theme_groups = []
            label_groups = []

        lines = [f"# {title}", "", f"Dear {audience},", ""]

        lines.append(self._opening_paragraph(role, label_groups))
        lines.append("")

        summary = self._first_source(
            contract.sources, {"professional_summary", "professionalsummary"}
        )
        if summary:
            lines.append(self._summary_text(summary))
            lines.append("")

        for para in self._body_paragraphs(evidence, theme_groups):
            lines.append(para)
            lines.append("")

        lines.append(self._closing_paragraph(name, role, label_groups))
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
            matched = [
                r for r in requirements
                if r in text or any(a in text for a in _REVERSE_REQ_ALIASES.get(r, ()))
            ]
            if matched:
                scored.append((source, len(matched), matched))

        scored.sort(key=lambda x: -x[1])
        return scored

    @staticmethod
    def _consolidate_requirements(
        matched_reqs: list[str],
    ) -> str:
        """Map a list of raw requirement tokens to a canonical theme key.

        Returns the theme with the most matching tokens, or the first
        raw token if no consolidation alias is found.
        """
        theme_counts: dict[str, int] = {}
        unmatched: list[str] = []
        for req in matched_reqs:
            canonical = _CONSOLIDATION_ALIASES.get(req)
            if canonical:
                theme_counts[canonical] = theme_counts.get(canonical, 0) + 1
            else:
                unmatched.append(req)

        if theme_counts:
            return max(theme_counts, key=theme_counts.get)  # type: ignore[arg-type]
        if unmatched:
            return unmatched[0]
        return matched_reqs[0] if matched_reqs else ""

    @staticmethod
    def _assign_themes(
        evidence: list[tuple[ExportSource, int, list[str]]],
    ) -> list[tuple[str, list[ExportSource], list[str]]]:
        """Consolidate requirements into themes and deduplicate evidence.

        Returns ``(theme_key, [sources], [raw_requirements])`` tuples.
        Each source appears in at most one theme.  Themes are returned in
        priority order (most discriminating first), limited to
        ``_MAX_BODY_PARAGRAPHS``.
        """
        # Step 1: assign each source to its best theme, track raw reqs
        theme_sources: dict[str, list[ExportSource]] = {}
        theme_reqs: dict[str, list[str]] = {}

        for source, _score, matched_reqs in evidence:
            theme = MarkdownInterestLetterGenerator._consolidate_requirements(matched_reqs)
            if not theme:
                continue
            theme_sources.setdefault(theme, []).append(source)
            theme_reqs.setdefault(theme, [])
            for r in matched_reqs:
                if r not in theme_reqs[theme]:
                    theme_reqs[theme].append(r)

        # Step 2: deduplicate — each source appears in at most one theme
        seen_sources: set[str] = set()
        deduped: dict[str, list[ExportSource]] = {}
        for theme, sources in theme_sources.items():
            unique = []
            for s in sources:
                if s.id not in seen_sources:
                    seen_sources.add(s.id)
                    unique.append(s)
            if unique:
                deduped[theme] = unique

        # Step 3: order by priority then by number of sources
        def _sort_key(item: tuple[str, list[ExportSource]]) -> tuple[int, int]:
            theme, sources = item
            try:
                priority = _THEME_PRIORITY.index(theme)
            except ValueError:
                priority = len(_THEME_PRIORITY)
            return (priority, -len(sources))

        sorted_themes = sorted(deduped.items(), key=_sort_key)
        result = [
            (theme, sources, theme_reqs.get(theme, []))
            for theme, sources in sorted_themes
        ]
        return result[: MarkdownInterestLetterGenerator._MAX_BODY_PARAGRAPHS]

    @staticmethod
    def _pooled_theme_groups(
        evidence: list[tuple[ExportSource, int, list[str]]],
    ) -> list[tuple[str, list[ExportSource], list[str]]]:
        """Rank themes by aggregate relevance across the selected evidence.

        Every requirement matched by any evidence source contributes to its
        canonical theme's relevance pool, so a theme earns a top rank from
        accumulated cross-source strength even when no single source claims
        it winner-take-all.  This aggregated ordering drives the opening and
        closing capability labels.  Source lists are empty because this
        ordering never narrates the letter body.
        """
        counts: dict[str, int] = {}
        for _source, _score, matched_reqs in evidence:
            for req in matched_reqs:
                canonical = _CONSOLIDATION_ALIASES.get(req)
                if canonical:
                    counts[canonical] = counts.get(canonical, 0) + 1

        def _sort_key(theme: str) -> tuple[int, int, str]:
            try:
                priority = _THEME_PRIORITY.index(theme)
            except ValueError:
                priority = len(_THEME_PRIORITY)
            return (-counts.get(theme, 0), priority, theme)

        return [(theme, [], []) for theme in sorted(counts, key=_sort_key)]

    # ------------------------------------------------------------------
    # Letter sections
    # ------------------------------------------------------------------

    def _opening_paragraph(
        self, role: object, theme_groups: list[tuple[str, list[ExportSource], list[str]]]
    ) -> str:
        """Build opening paragraph referencing top capability areas."""
        labels = self._capability_labels(theme_groups)

        if role and labels:
            req_text = self._join_requirements(labels)
            return (
                f"I am writing to express strong interest in the {role} opportunity. "
                f"My background in {req_text} aligns closely with this role."
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
        self,
        evidence: list[ExportSource],
        theme_groups: list[tuple[str, list[ExportSource], list[str]]],
    ) -> list[str]:
        """Build body paragraphs connecting themes to evidence.

        Each paragraph connects one theme to its best matching evidence
        using natural prose.  Evidence is deduplicated across paragraphs.
        """
        paragraphs: list[str] = []
        if theme_groups:
            matched_by_id: dict[str, set[str]] = {}
            for _source, _score, matched_reqs in evidence:
                matched_by_id.setdefault(_source.id, set()).update(matched_reqs)
            for idx, (theme, sources, raw_reqs) in enumerate(theme_groups):
                para = self._narrative_paragraph(
                    theme, sources, raw_reqs, idx, matched_by_id=matched_by_id
                )
                if para:
                    paragraphs.append(para)
        else:
            for source in evidence[: self._MAX_BODY_PARAGRAPHS]:
                desc = self._strip_terminal_punctuation(self._source_prose(source))
                if desc:
                    paragraphs.append(f"{self._lower_first(desc)}.")
        return paragraphs

    def _narrative_paragraph(
        self,
        theme: str,
        sources: list[ExportSource],
        raw_reqs: list[str],
        para_idx: int,
        matched_by_id: dict[str, set[str]] | None = None,
    ) -> str:
        """Build a natural narrative paragraph for one theme group.

        Uses ``para_idx`` (0, 1, 2) to vary sentence openers
        deterministically across paragraphs.
        """
        exp_sources = [s for s in sources if s.type.lower() == "experience"]
        skill_sources = [s for s in sources if s.type.lower() == "skill"]
        cert_sources = [s for s in sources if s.type.lower() == "certification"]
        other_sources = [
            s for s in sources
            if s.type.lower() not in ("experience", "skill", "certification")
        ]

        sentences: list[str] = []

        # --- Lead sentence with supporting details woven in ---
        if exp_sources:
            exp = exp_sources[0]
            title = exp.data.get("title", exp.id)
            scope = self._first_clause(exp.data.get("scope", ""))
            scope_l = (
                self._lower_first(self._strip_terminal_punctuation(scope))
                if scope
                else "contributed to key initiatives"
            )

            # Drop skills already implied by the experience scope
            scope_lower = scope.lower()
            skill_sources = [
                s for s in skill_sources
                if s.data.get("name", "").lower() not in scope_lower
            ]

            supporting = self._build_supporting_clause(skill_sources, cert_sources, para_idx)

            _exp_leads = [
                f"In my role as {title}, I {scope_l}",
                f"As {title}, I {scope_l}",
                f"Working as {title}, I {scope_l}",
            ]
            lead = _exp_leads[para_idx % len(_exp_leads)]

            if supporting:
                sentences.append(f"{lead}, {supporting}.")
            else:
                sentences.append(f"{lead}.")

            second = self._pick_second_experience(exp, exp_sources[1:], matched_by_id, scope_l)
            if second is not None:
                sentences.append(self._additional_experience_sentence(second, para_idx))
        elif skill_sources:
            names = [s.data.get("name", s.id) for s in skill_sources[:3]]
            area = self._join_requirements(names)

            detail = ""
            for s in skill_sources[:1]:
                desc = self._clean_skill_desc(s.data.get("description", ""))
                if desc:
                    detail = f", including {self._lower_first(desc)}"
                    break

            _skill_leads = [
                f"I bring strong expertise in {area}{detail}",
                f"My technical capabilities span {area}{detail}",
                f"My experience includes {area}{detail}",
            ]
            sentences.append(_skill_leads[para_idx % len(_skill_leads)] + ".")
        elif cert_sources:
            for s in cert_sources[:1]:
                name = s.data.get("name", s.id)
                if "cert" in name.lower():
                    sentences.append(f"My background includes {name}.")
                else:
                    sentences.append(f"My background includes {name} certification.")

        # --- Other sources (projects, achievements) rendered separately ---
        for s in other_sources[:1]:
            prose = self._source_prose(s)
            if prose:
                sentences.append(
                    self._upper_first(self._strip_terminal_punctuation(prose)) + "."
                )

        return " ".join(sentences)

    @staticmethod
    def _pick_second_experience(
        anchor: ExportSource,
        candidates: list[ExportSource],
        matched_by_id: dict[str, set[str]] | None,
        anchor_scope_l: str,
    ) -> ExportSource | None:
        """Pick the strongest additional same-theme experience to narrate.

        Prefers the candidate contributing the most distinct matched
        requirements not already covered by the anchor experience (materially
        new evidence), tie-breaking by total match count, then source id for
        full determinism.  Returns ``None`` when no candidate adds distinct
        evidence or every candidate duplicates the anchor scope text.
        """
        if not candidates or not matched_by_id:
            return None
        anchor_reqs = matched_by_id.get(anchor.id, set())
        best: ExportSource | None = None
        best_key: tuple[int, int, str] | None = None
        for candidate in candidates:
            cand_reqs = matched_by_id.get(candidate.id, set())
            distinct = cand_reqs - anchor_reqs
            if not distinct:
                continue
            scope = MarkdownInterestLetterGenerator._first_clause(
                candidate.data.get("scope", "")
            )
            if MarkdownInterestLetterGenerator._lower_first(scope) == anchor_scope_l:
                continue
            key = (-len(distinct), -len(cand_reqs), candidate.id)
            if best_key is None or key < best_key:
                best, best_key = candidate, key
        return best

    @staticmethod
    def _additional_experience_sentence(
        candidate: ExportSource, para_idx: int
    ) -> str:
        """Build one natural sentence narrating a second same-theme experience.

        Uses the same deterministic lead templates as the anchor sentence,
        offset by one so the two openers never repeat verbatim.
        """
        title = candidate.data.get("title", candidate.id)
        scope = MarkdownInterestLetterGenerator._first_clause(
            candidate.data.get("scope", "")
        )
        if scope:
            scope_l = MarkdownInterestLetterGenerator._lower_first(
                MarkdownInterestLetterGenerator._strip_terminal_punctuation(scope)
            )
        else:
            scope_l = "contributed to key initiatives"
        leads = [
            f"In my role as {title}, I {scope_l}",
            f"As {title}, I {scope_l}",
            f"Working as {title}, I {scope_l}",
        ]
        return f"{leads[(para_idx + 1) % len(leads)]}."

    def _build_supporting_clause(
        self,
        skill_sources: list[ExportSource],
        cert_sources: list[ExportSource],
        para_idx: int,
    ) -> str | None:
        """Build a natural supporting clause from skills and certifications.

        Combines up to 2 skills and 1 certification into a single flowing
        clause that attaches to the experience lead sentence.
        """
        parts: list[str] = []

        for s in skill_sources[:2]:
            name = s.data.get("name", s.id)
            desc = self._clean_skill_desc(s.data.get("description", ""))
            if desc:
                parts.append(f"{name} ({self._lower_first(desc)})")
            else:
                parts.append(name)

        for s in cert_sources[:1]:
            name = s.data.get("name", s.id)
            if "cert" in name.lower():
                parts.append(name)
            else:
                parts.append(f"{name} certification")

        if not parts:
            return None

        connectors = ["using", "leveraging", "with", "applying"]
        connector = connectors[para_idx % len(connectors)]

        if len(parts) == 1:
            return f"{connector} {parts[0]}"
        if len(parts) == 2:
            return f"{connector} {parts[0]} and {parts[1]}"
        return f"{connector} {parts[0]}, {parts[1]}, and {parts[2]}"

    def _closing_paragraph(
        self,
        name: str,
        role: object,
        theme_groups: list[tuple[str, list[ExportSource], list[str]]],
    ) -> str:
        """Build closing paragraph referencing role and strongest fit.

        The closing reflects the aggregate theme ranking (top two pooled
        themes, joined deterministically), so a distributed thread like
        ``cloud_infra`` surfaces here even when it is not the single top
        theme in the aggregated pool.
        """
        if not role:
            return "Sincerely,"

        strongest = ""
        if theme_groups:
            labels = self._capability_labels(theme_groups[:2])
            if labels:
                strongest = self._join_requirements(labels)

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

    def _capability_labels(
        self, theme_groups: list[tuple[str, list[ExportSource], list[str]]]
    ) -> list[str]:
        """Extract human-readable capability labels from theme groups.

        Each canonical theme is mapped to its curated display label.  Raw
        requirement tokens are never used: curated labels are stable and
        grammatical, so generic JD verbs or malformed multi-line tokens can
        never surface as a capability label.
        """
        labels: list[str] = []
        for theme, _sources, _raw_reqs in theme_groups[:3]:
            label = _THEME_LABELS.get(theme)
            if label:
                labels.append(label)
        return labels

    @staticmethod
    def _clean_skill_desc(desc: str) -> str:
        """Strip leading 'Expert in', 'Proficient in', etc. and terminal punctuation."""
        if not desc:
            return ""
        cleaned = desc
        for prefix in ("Expert in ", "Proficient in ", "Skilled in ", "Experienced in "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        return MarkdownInterestLetterGenerator._strip_terminal_punctuation(cleaned)

    @staticmethod
    def _strip_terminal_punctuation(text: str) -> str:
        """Remove trailing sentence punctuation and whitespace before embedding.

        Prevents artifacts such as ``.).`` or ``..`` when a source description
        or scope fragment (which may end with ``.``) is wrapped in parentheses
        or placed mid-sentence.
        """
        if not text:
            return ""
        return re.sub(r"[.!?\s]+$", "", text)

    @staticmethod
    def _upper_first(text: str) -> str:
        """Capitalize the first character."""
        if not text:
            return ""
        return text[0].upper() + text[1:]

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
        if token in _ACronyms:
            return token.upper()
        if "/" in token:
            return "/".join(
                p.upper() if p in _ACronyms else p.title() for p in token.split("/")
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
