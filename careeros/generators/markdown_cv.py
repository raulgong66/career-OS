"""Markdown CV generator — produces recruiter-quality CVs."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from ..exceptions import LLMConfigurationError, ValidationError
from ..export_contract import ExportContract, ExportSource

logger = logging.getLogger(__name__)


class MarkdownCVGenerator:
    """Generate recruiter-quality Markdown CVs from an export contract.

    Two modes:
      - Deterministic (no JD):  professional CV using structured profile data.
      - LLM-powered   (with JD): synthesises content from profile + job description.
    """

    supported_artifact_types = {"CV", "RESUME"}

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        self._llm_config = llm_config

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(self, contract: ExportContract) -> str:
        artifact_type = contract.artifact_type.upper()
        if artifact_type not in self.supported_artifact_types:
            raise ValidationError(
                f"Unsupported artifact type for Markdown CV: {contract.artifact_type}"
            )

        cv_llm = (os.environ.get("CV_LLM_ENABLED") or "").strip().lower() in ("true", "1", "yes")
        if cv_llm and contract.job_description:
            try:
                return self._llm_generate(contract)
            except Exception as exc:
                logger.warning("LLM CV generation failed, falling back to deterministic: %s", exc)

        return self._deterministic_generate(contract)

    # ------------------------------------------------------------------
    # LLM-powered generation (with job description)
    # ------------------------------------------------------------------

    def _llm_generate(self, contract: ExportContract) -> str:
        prompt = self._build_llm_prompt(contract)
        raw = self._call_llm(prompt)
        return self._parse_llm_response(raw)

    def _build_llm_prompt(self, contract: ExportContract) -> str:
        person = contract.person
        artifact = contract.artifact

        def safe(val: Any) -> str:
            return str(val) if val else ""

        # ── person block ──────────────────────────────────────────────
        name = self._person_name(person)
        headline = safe(person.get("positioning", {}).get("headline"))
        email = safe(person.get("email"))
        phone = safe(person.get("phone"))
        city = safe(person.get("city"))
        country = safe(person.get("country"))
        location = ", ".join(filter(None, [city, country]))
        linkedin = safe(person.get("linkedin"))
        github = safe(person.get("github"))
        languages_raw = person.get("languages", [])
        languages = ", ".join(
            f"{l.get('name', '')} ({l.get('proficiency', '')})"
            for l in languages_raw if l.get("name")
        )

        # ── summaries ─────────────────────────────────────────────────
        summaries = []
        for s in contract.sources:
            if s.type.lower() in ("professional_summary", "professionalsummary"):
                text = s.data.get("text") or s.data.get("label", "")
                if text:
                    summaries.append(text)

        # ── experiences ───────────────────────────────────────────────
        experiences = []
        for s in contract.sources:
            if s.type.lower() != "experience":
                continue
            d = s.data
            exp = {
                "title": safe(d.get("title")),
                "organization": safe(d.get("organization")),
                "start": safe(d.get("dateRange", {}).get("start") or d.get("startDate", "")),
                "end": safe(d.get("dateRange", {}).get("end") or d.get("endDate", "")),
                "isCurrent": d.get("dateRange", {}).get("isCurrent", False) or d.get("isCurrent", False),
                "location": safe(d.get("location")),
                "scope": safe(d.get("scope")),
                "responsibilities": d.get("responsibilities", []),
                "achievements": d.get("achievements", []),
                "technologies": d.get("technologies", []),
            }
            experiences.append(exp)

        # ── skills ────────────────────────────────────────────────────
        skills = []
        for s in contract.sources:
            if s.type.lower() != "skill":
                continue
            d = s.data
            skills.append({
                "name": safe(d.get("name")),
                "category": safe(d.get("category")),
                "proficiency": safe(d.get("proficiency")),
            })

        # ── education ─────────────────────────────────────────────────
        education_entries = []
        for s in contract.sources:
            if s.type.lower() != "education":
                continue
            d = s.data
            education_entries.append({
                "institution": safe(d.get("institution")),
                "program": safe(d.get("program")),
                "degree": safe(d.get("degree")),
                "field": safe(d.get("fieldOfStudy")),
                "start": safe(d.get("dateRange", {}).get("start")),
                "end": safe(d.get("dateRange", {}).get("end")),
                "isCurrent": d.get("dateRange", {}).get("isCurrent", False),
            })

        # ── certifications ────────────────────────────────────────────
        certs = []
        for s in contract.sources:
            if s.type.lower() != "certification":
                continue
            d = s.data
            certs.append({
                "name": safe(d.get("name")),
                "issuer": safe(d.get("issuer")),
                "date": safe(d.get("dateRange", {}).get("label") or d.get("dateRange", {}).get("end", "")),
            })

        # ── projects ──────────────────────────────────────────────────
        projects = []
        for s in contract.sources:
            if s.type.lower() != "project":
                continue
            d = s.data
            projects.append({
                "name": safe(d.get("name")),
                "description": safe(d.get("description")),
                "technologies": d.get("technologies", []),
                "url": safe(d.get("url")),
            })

        # ── reasoning ─────────────────────────────────────────────────
        r = contract.reasoning
        competencies = self._skill_competencies(contract)
        core_comp = ", ".join(competencies)
        selected_skill_names = {
            str(s.data.get("name", "")).strip().lower()
            for s in contract.sources
            if s.type.lower() == "skill" and s.data.get("name")
        }
        backed = (
            [i for i in r.strongest_skills if str(i).strip().lower() in selected_skill_names]
            if r and r.strongest_skills
            else []
        )
        top_skills = ", ".join(backed)
        tech_breadth = ", ".join(r.technology_breadth) if r and r.technology_breadth else ""
        career_stage = r.career_stage if r and r.career_stage else ""
        domain_exp = ", ".join(r.domain_expertise) if r and r.domain_expertise else ""

        profile_json = json.dumps({
            "name": name,
            "headline": headline,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin": linkedin,
            "github": github,
            "languages": languages,
            "summaries": summaries,
            "experiences": experiences,
            "skills": skills,
            "education": education_entries,
            "certifications": certs,
            "projects": projects,
            "reasoning": {
                "core_competencies": core_comp,
                "strongest_skills": top_skills,
                "technology_breadth": tech_breadth,
                "career_stage": career_stage,
                "domain_expertise": domain_exp,
            },
        }, indent=2)

        jd = contract.job_description.strip()

        return f"""You are a professional CV writer. Generate a recruiter-quality CV in Markdown.

Use the profile data and job description below. The CV must follow this structure:

# Full Name
Contact line (headline | location | email)

## Professional Summary
3-4 sentences synthesising the professional profile with the job description. Highlight the strongest alignment.

## Core Competencies
Comma-separated list of 6-10 key competencies drawn from skills, reasoning, and JD relevance.

## Professional Experience
For each role, render as plain text (no Markdown headings for roles):
Job Title at Company
Start – End | Location
• 3-6 bullet-point achievements (not responsibilities). Prioritise achievements relevant to the JD.
• Use strong action verbs and quantify where possible.
• Technologies: tech1, tech2, tech3

## Projects (if available)

## Education

## Certifications

Rules:
- Only the major sections use headings: # Candidate Name, ## Professional Summary, ## Core Competencies, ## Professional Experience, ## Projects, ## Education, ## Certifications.
- Never use heading syntax (### or deeper) for individual roles, projects, education entries, or certifications.
- Use bullet points with the character "•" (U+2022), never hyphens.
- Write in active voice, third person implied.
- Keep bullet points concise (1-2 lines each).
- Order experiences most-recent-first.
- Emphasise content relevant to the job description.
- Never invent facts not in the profile data.
- Use the job description to guide skill ordering, experience emphasis, and wording.
- Output ONLY a JSON object with a single key "cv" containing the full Markdown CV as a string.
- Do not wrap the JSON in markdown fences.

Profile data:
{profile_json}

Job Description:
{jd}
"""

    def _call_llm(self, prompt: str) -> str:
        provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()

        if provider == "ollama":
            return self._call_ollama(prompt)
        elif provider == "openai":
            return self._call_openai(prompt)
        else:
            raise LLMConfigurationError(
                f"Cannot generate CV: LLM_PROVIDER={provider!r} is not configured. "
                "Set LLM_PROVIDER in .env"
            )

    def _call_ollama(self, prompt: str) -> str:
        host = (os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        model = os.environ.get("OLLAMA_MODEL") or "qwen2.5:3b"

        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")

    def _call_openai(self, prompt: str) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "OpenAI API key is required. Set OPENAI_API_KEY in .env"
            )
        model = os.environ.get("OPENAI_MODEL") or "gpt-4o"

        with httpx.Client(timeout=120) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            choices = response.json().get("choices", [])
            if not choices:
                raise LLMConfigurationError("OpenAI returned no choices")
            return choices[0].get("message", {}).get("content", "")

    def _parse_llm_response(self, raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"Failed to parse LLM CV response as JSON: {exc}\nRaw:\n{raw}"
                ) from exc

        if not isinstance(data, dict):
            raise ValidationError("LLM CV response is not a JSON object")

        cv = data.get("cv") or data.get("markdown") or data.get("content", "")
        if not cv:
            raise ValidationError(
                "LLM CV response missing 'cv' key. Keys: " + ", ".join(data.keys())
            )
        return str(cv).strip() + "\n"

    # ------------------------------------------------------------------
    # Deterministic generation (no job description)
    # ------------------------------------------------------------------

    def _deterministic_generate(self, contract: ExportContract) -> str:
        lines: list[str] = []
        lines.extend(self._render_header(contract))
        lines.append("")

        summary = self._render_summary(contract)
        if summary:
            lines.append("## Professional Summary")
            lines.append(summary)
            lines.append("")

        competencies = self._render_core_competencies(contract)
        if competencies:
            lines.append("## Core Competencies")
            lines.append(competencies)
            lines.append("")

        self._render_experience_section(lines, contract)
        self._render_projects_section(lines, contract)
        self._render_education_section(lines, contract)
        self._render_certifications_section(lines, contract)

        return "\n".join(lines).strip() + "\n"

    # ── header ────────────────────────────────────────────────────────

    def _render_header(self, contract: ExportContract) -> list[str]:
        person = contract.person
        name = self._person_name(person)

        headline = person.get("positioning", {}).get("headline")
        email = person.get("email")
        phone = person.get("phone")
        city = person.get("city")
        country = person.get("country")
        location = ", ".join(filter(None, [city, country]))
        linkedin = person.get("linkedin")

        parts = list(filter(None, [headline, location, email, phone]))
        lines = [f"# {name}"]
        if parts:
            lines.append(" | ".join(str(p) for p in parts))
        if linkedin:
            lines.append(str(linkedin))
        return lines

    # ── summary ──────────────────────────────────────────────────────

    def _render_summary(self, contract: ExportContract) -> str:
        for s in contract.sources:
            if s.type.lower() in ("professional_summary", "professionalsummary"):
                text = s.data.get("text") or s.data.get("label", "")
                if text:
                    return str(text)
        r = contract.reasoning
        if r and r.career_stage:
            parts = [f"{self._person_name(contract.person)} is a {r.career_stage} professional."]
            if r.domain_expertise:
                parts.append(f"Deep expertise in {', '.join(r.domain_expertise)}.")
            if r.technology_breadth:
                parts.append(f"Proficient across {', '.join(r.technology_breadth)}.")
            if r.core_competencies:
                parts.append(f"Core competencies include {', '.join(r.core_competencies)}.")
            return " ".join(parts)
        return ""

    # ── core competencies ─────────────────────────────────────────────

    def _skill_competencies(self, contract: ExportContract) -> list[str]:
        """Context-aware competency names from selected sources + reasoning.

        Reasoning-derived skill names (strongest skills, core competencies)
        are only kept when backed by a context-selected skill source, so
        skills scoped to other target contexts never leak into the CV.
        """
        seen: set[str] = set()
        items: list[str] = []

        selected_skill_names = {
            str(s.data.get("name", "")).strip().lower()
            for s in contract.sources
            if s.type.lower() == "skill" and s.data.get("name")
        }

        def _add(group: list[str], required_backing: bool = False) -> None:
            for item in group:
                name = str(item).strip()
                key = name.lower()
                if not name or key in seen:
                    continue
                if required_backing and key not in selected_skill_names:
                    continue
                seen.add(key)
                items.append(name)

        r = contract.reasoning
        if r:
            _add(r.technology_breadth)
            _add(r.domain_expertise)
            _add(r.core_competencies, required_backing=True)
            _add(r.strongest_skills, required_backing=True)

        for s in contract.sources:
            if s.type.lower() == "skill":
                _add([str(s.data.get("name", "")).strip()])

        return items

    def _render_core_competencies(self, contract: ExportContract) -> str:
        items = self._skill_competencies(contract)
        if items:
            return ", ".join(items)
        return ""

    # ── experience ────────────────────────────────────────────────────

    def _render_experience_section(self, lines: list[str], contract: ExportContract) -> None:
        experiences = [s for s in contract.sources if s.type.lower() == "experience"]
        if not experiences:
            return

        lines.append("## Professional Experience")
        for s in experiences:
            d = s.data
            title = str(d.get("title", "")).strip()
            org = str(d.get("organization", "")).strip()
            lines.append(title or org or s.id)
            if title and org:
                lines.append(org)

            dr = d.get("dateRange", {}) if isinstance(d.get("dateRange"), dict) else {}
            start = dr.get("start") or d.get("startDate", "")
            end = dr.get("end") or d.get("endDate", "")
            is_current = dr.get("isCurrent", False) or d.get("isCurrent", False)
            loc = d.get("location", "")
            date_str = self._date_range_str(start, end, is_current)
            meta_parts = list(filter(None, [date_str, loc]))
            if meta_parts:
                lines.append(" | ".join(str(p) for p in meta_parts))

            bullets: list[str] = []
            achievements = d.get("achievements", [])
            responsibilities = d.get("responsibilities", [])

            for a in achievements:
                text = a.get("statement") or (a if isinstance(a, str) else "")
                if text:
                    bullets.append(str(text))

            for r_item in responsibilities:
                text = r_item.get("description") or (r_item if isinstance(r_item, str) else "")
                if text:
                    bullets.append(str(text))

            if not bullets and d.get("scope"):
                bullets.append(str(d["scope"]))

            technologies = d.get("technologies", [])
            if isinstance(technologies, list) and technologies:
                tech_str = ", ".join(str(t) for t in technologies)
                bullets.append(f"Technologies: {tech_str}")

            if bullets:
                lines.append("")
                for b in bullets[:8]:
                    lines.append(f"• {b}")

            lines.append("")

    def _date_range_str(self, start: Any, end: Any, is_current: bool) -> str:
        start = str(start).strip() if start else ""
        if is_current:
            if start:
                return f"{start} – Present"
            return "Present"
        end = str(end).strip() if end else ""
        if start and end:
            return f"{start} – {end}"
        return start or end or ""

    # ── projects ──────────────────────────────────────────────────────

    def _render_projects_section(self, lines: list[str], contract: ExportContract) -> None:
        projects = [s for s in contract.sources if s.type.lower() == "project"]
        if not projects:
            return

        lines.append("## Projects")
        for s in projects:
            d = s.data
            name = str(d.get("name", "")).strip() or s.id
            desc = d.get("description")
            techs = d.get("technologies", [])
            url = d.get("url")
            parts = [f"**{name}**"]
            if desc:
                parts.append(f": {str(desc).strip()}")
            lines.append("".join(parts))
            if techs and isinstance(techs, list):
                lines.append(f"  • Technologies: {', '.join(str(t) for t in techs)}")
            if url:
                lines.append(f"  • {str(url).strip()}")
        lines.append("")

    # ── education ─────────────────────────────────────────────────────

    @staticmethod
    def _education_label(data: dict[str, Any], fallback: str) -> str:
        """Render a concise education label from schema-compatible data."""
        program = str(data.get("program", "")).strip()
        field = str(data.get("fieldOfStudy", "")).strip()
        degree = str(data.get("degree", "")).strip()
        institution = str(data.get("institution", "")).strip()
        label_parts = list(filter(None, [program or degree, f"in {field}" if field else ""]))
        return " ".join(label_parts) if label_parts else institution or fallback

    def _render_education_section(self, lines: list[str], contract: ExportContract) -> None:
        edu = [s for s in contract.sources if s.type.lower() == "education"]
        if not edu:
            return

        lines.append("## Education")
        for s in edu:
            d = s.data
            institution = str(d.get("institution", "")).strip()

            label = self._education_label(d, s.id)

            dr = d.get("dateRange", {})
            if isinstance(dr, dict):
                start = dr.get("start", "")
                end = dr.get("end", "")
                is_current = dr.get("isCurrent", False)
            else:
                start = end = ""
                is_current = False
            date_str = self._date_range_str(start, end, is_current)

            line = label
            if institution:
                line = f"{label}, {institution}" if label != institution else institution
            if date_str:
                line = f"{line} ({date_str})"

            lines.append(f"• {line}")
        lines.append("")

    # ── certifications ────────────────────────────────────────────────

    def _render_certifications_section(self, lines: list[str], contract: ExportContract) -> None:
        certs = [s for s in contract.sources if s.type.lower() == "certification"]
        if not certs:
            return

        lines.append("## Certifications")
        for s in certs:
            d = s.data
            name = str(d.get("name", "")).strip() or s.id
            issuer = d.get("issuer")
            dr = d.get("dateRange", {})
            date_str = ""
            if isinstance(dr, dict):
                date_str = str(dr.get("label") or dr.get("end", "")).strip()

            parts = [name]
            if issuer:
                parts.append(f"– {str(issuer).strip()}")
            if date_str:
                parts.append(f"({date_str})")
            lines.append(f"• {' '.join(parts)}")
        lines.append("")

    # ── person name helper ────────────────────────────────────────────

    @staticmethod
    def _person_name(person: dict[str, Any]) -> str:
        for name in person.get("names", []):
            if name.get("usage") == "professional" and name.get("value"):
                return str(name["value"])
        for name in person.get("names", []):
            if name.get("value"):
                return str(name["value"])
        first = person.get("firstName") or ""
        last = person.get("lastName") or ""
        full = person.get("fullName") or ""
        return full or f"{first} {last}".strip() or str(person.get("id", "Unnamed Profile"))
