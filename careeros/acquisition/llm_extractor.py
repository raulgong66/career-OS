from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from careeros.exceptions import CareerOSException, LLMConfigurationError

from careeros.ai import AIError, AIProvider, create_ai_provider
from careeros.ai.ollama_provider import OllamaProvider
from careeros.ai.openai_provider import OpenAIProvider

from .person_data import EducationData, ExperienceData, ExtractionResult, PersonData, SkillData

logger = logging.getLogger(__name__)


class LLMExtractionError(CareerOSException):
    pass


class TruncatedResponseError(LLMExtractionError):
    """Raised when the LLM response JSON is cut off before it completes.

    Signifies output-limit/context-window exhaustion rather than malformed
    content. ``LLMExtractor`` uses it to trigger a split-and-retry pass.
    """


_TOP_LEVEL_ALIASES: dict[str, str] = {
    "PersonalDetails": "person",
    "PersonDetails": "person",
    "WorkExperience": "experiences",
    "Experiences": "experiences",
    "Skills": "skills",
    "Education": "education",
}

_PERSON_FIELD_ALIASES: dict[str, str] = {
    "FullName": "fullName",
    "Name": "fullName",
    "Email": "email",
    "Phone": "phone",
    "City": "location",
    "LinkedIn": "linkedin",
    "Github": "github",
}

_EXPERIENCE_FIELD_ALIASES: dict[str, str] = {
    "Company": "organization",
    "Employer": "organization",
    "Role": "title",
    "Position": "title",
    "JobTitle": "title",
    "EmploymentType": "employmentType",
    "Responsibilities": "responsibilities",
    "Achievements": "achievements",
    "Technologies": "technologies",
    "Location": "location",
    "Summary": "summary",
}

_SKILL_FIELD_ALIASES: dict[str, str] = {
    "Skill": "name",
    "Technology": "name",
    "Category": "category",
    "Proficiency": "proficiency",
}

_EDUCATION_FIELD_ALIASES: dict[str, str] = {
    "School": "institution",
    "University": "institution",
    "Degree": "degree",
    "Field": "fieldOfStudy",
}

_MONTH_NUMBERS: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_DURATION_SPLIT_RE = re.compile(r"\s*[-–—]\s*")
_MONTH_YEAR_RE = re.compile(r"^(?P<mon>[A-Za-z]+)\s*(?P<yr>\d{4})")
_YEAR_RE = re.compile(r"^(?P<yr>\d{4})$")
_CURRENT_WORDS = {"present", "current", "now", "ongoing", "till date", "to date"}


class LLMExtractor:
    """Acquisition-domain service: extract structured profile data via an AI provider.

    Prompt construction and response parsing are business logic and stay here.
    The provider (an ``AIProvider``) only supplies the ``generate`` capability.
    """

    extraction_temperature = 0.1
    extraction_timeout = 60.0
    extraction_max_tokens = 6000
    chunk_size = 6000
    chunk_overlap = 300
    max_split_depth = 2

    def __init__(
        self,
        provider: AIProvider | None = None,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.provider = provider
        if chunk_size is not None:
            self.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.chunk_overlap = chunk_overlap

    def _resolve_provider(self) -> AIProvider:
        if self.provider is None:
            self.provider = create_ai_provider()
        return self.provider

    def _complete(self, prompt: str) -> str:
        try:
            return self._resolve_provider().generate(
                prompt,
                temperature=self.extraction_temperature,
                timeout=self.extraction_timeout,
                max_tokens=self.extraction_max_tokens,
                json_mode=True,
            )
        except AIError as exc:
            raise LLMExtractionError(f"LLM call failed: {exc}") from exc

    def extract(
        self, text: str, schema: dict[str, Any] | None = None
    ) -> ExtractionResult:
        chunks = self.chunk_text(text)
        if len(chunks) == 1:
            return self._extract_chunk(chunks[0], schema)
        logger.debug("Extracting %d chunks from a %d-char document", len(chunks), len(text))
        results = [self._extract_chunk(chunk, schema) for chunk in chunks]
        merged = self.merge_results(results)
        merged.warnings.append(
            f"Document was split into {len(chunks)} chunks for extraction."
        )
        return merged

    def _extract_chunk(
        self, text: str, schema: dict[str, Any] | None, depth: int = 0
    ) -> ExtractionResult:
        try:
            return self._extract_once(text, schema)
        except TruncatedResponseError as exc:
            if depth >= self.max_split_depth:
                raise
            halves = self._split_text(text)
            if len(halves) < 2:
                raise
            logger.debug(
                "Chunk (%d chars) hit the output limit; splitting into %d parts",
                len(text),
                len(halves),
            )
            parts = [self._extract_chunk(part, schema, depth=depth + 1) for part in halves]
            merged = self.merge_results(parts)
            merged.warnings.append(
                "A chunk exceeded the model output limit and was split for retry."
            )
            return merged

    def _extract_once(self, text: str, schema: dict[str, Any] | None) -> ExtractionResult:
        prompt = self.build_prompt(text, schema)
        response = self._complete(prompt)
        data = self.parse_response(response)
        return self.to_result(data)

    def chunk_text(self, text: str) -> list[str]:
        """Split a document into extraction-sized chunks with overlap.

        Documents that fit within ``chunk_size`` chars are returned whole so
        small CVs keep the exact single-shot behaviour. Chunks prefer line
        boundaries; a single line longer than ``chunk_size`` is hard-split so
        no chunk ever exceeds the budget. Overlap prevents an entry that
        straddles a boundary from being lost; downstream builders deduplicate
        the resulting overlap.
        """
        if len(text) <= self.chunk_size:
            return [text]
        chunks: list[str] = []
        current = ""
        for line in text.splitlines(keepends=True):
            if current and len(current) + len(line) > self.chunk_size:
                chunks.append(current)
                current = self._overlap_tail(current)
            while line and len(current) + len(line) > self.chunk_size:
                take = self.chunk_size - len(current)
                if take <= 0:
                    take = self.chunk_size
                piece = current + line[:take]
                chunks.append(piece)
                current = self._overlap_tail(piece)
                line = line[take:]
            current += line
        if current:
            chunks.append(current)
        return chunks

    def _overlap_tail(self, text: str) -> str:
        if self.chunk_overlap <= 0 or len(text) <= self.chunk_overlap:
            return ""
        return text[-self.chunk_overlap :]

    def _split_text(self, text: str) -> list[str]:
        """Split a chunk into two overlapping halves at a line boundary."""
        if len(text) < 2:
            return [text]
        lines = text.splitlines(keepends=True)
        target = len(text) / 2
        first = ""
        for line in lines:
            if first and len(first) + len(line) > target:
                break
            first += line
        rest = text[len(first) :]
        if not first or not rest:
            mid = len(text) // 2
            return [text[:mid], text[mid:]]
        return [first, self._overlap_tail(first) + rest]

    def merge_results(self, results: list[ExtractionResult]) -> ExtractionResult:
        """Deterministically merge per-chunk extraction results.

        Person fields take the first non-empty value in chunk order. Experience,
        skill, and education entities are concatenated and deduplicated later by
        the canonical builders, so nothing extracted from any chunk is dropped.
        """
        results = [r for r in results if r is not None]
        if not results:
            return ExtractionResult(
                person=PersonData(id="person-unknown", first_name="", last_name="", full_name="")
            )
        return ExtractionResult(
            person=self._merge_person([r.person for r in results]),
            experiences=[exp for r in results for exp in r.experiences],
            skills=[skill for r in results for skill in r.skills],
            education=[edu for r in results for edu in r.education],
            warnings=[w for r in results for w in r.warnings],
        )

    @staticmethod
    def _merge_person(people: list[PersonData]) -> PersonData:
        def first_value(getter) -> Any:
            for person in people:
                value = getter(person)
                if value:
                    return value
            return None

        return PersonData(
            id=first_value(
                lambda p: p.id if p.id and p.id != "person-unknown" else None
            )
            or "person-unknown",
            first_name=first_value(lambda p: p.first_name) or "",
            last_name=first_value(lambda p: p.last_name) or "",
            full_name=first_value(lambda p: p.full_name) or "",
            email=first_value(lambda p: p.email),
            phone=first_value(lambda p: p.phone),
            location=first_value(lambda p: p.location),
            linkedin=first_value(lambda p: p.linkedin),
            github=first_value(lambda p: p.github),
        )

    def build_prompt(self, text: str, schema: dict[str, Any] | None = None) -> str:
        prompt = (
            "You are a professional profile data extractor. "
            "Given a resume or CV document text, extract the person's identity, "
            "contact information, professional experience, and skills.\n\n"
            "Return ONLY a JSON object with four top-level sections: "
            '"person", "experiences", "skills", and "education".\n'
            '(Do not include markdown formatting, code fences, or extra text.)\n\n'
            "--- person section ---\n"
            "- id: a unique slug based on the person's last name (e.g. \"person-gongora\")\n"
            "- firstName: the person's first name\n"
            "- lastName: the person's last name\n"
            "- fullName: the person's full name as it appears on the document\n"
            "- email: the person's email address (omit if not found)\n"
            "- phone: the person's phone number (omit if not found)\n"
            "- location: the person's location, typically city and country (omit if not found)\n"
            "- linkedin: full LinkedIn profile URL (omit if not found)\n"
            "- github: full GitHub profile URL (omit if not found)\n\n"
            "--- experiences section ---\n"
            "An array of experience objects, most recent first. "
            "Each experience object has these fields:\n"
            '- id: a unique slug for this experience (e.g. "exp-qred-bank")\n'
            "- organization: the employer or client company name\n"
            "- title: the role title\n"
            '- employmentType: "Full-time", "Contract", "Self-employed", etc. '
            "(omit if not clear)\n"
            "- location: where the role was based (omit if not found)\n"
            '- startDate: start date (e.g. "2022-03", "2020", or full date)\n'
            '- endDate: end date, or null if current (e.g. "2025-01")\n'
            "- isCurrent: boolean, true if the person currently holds this role\n"
            "- summary: a brief overview of the role (omit if not found)\n"
            "- responsibilities: an array of responsibility descriptions\n"
            "- achievements: an array of notable achievements or results in this role\n"
            "- technologies: an array of technologies, tools, or platforms used\n"
            '- sourceRef: a short label indicating where this data came from '
            '(omit if not found)\n\n'
            "--- skills section ---\n"
            "An array of skill objects extracted from the document. "
            "Each skill object has these fields:\n"
            '- id: a unique slug for this skill (e.g. "skill-python")\n'
            "- name: the skill name (e.g. \"Python\", \"AWS\", \"Kubernetes\")\n"
            '- category: the skill category (e.g. "Programming Language", '
            '"Cloud Platform", "Tool") — omit if not clear\n'
            '- proficiency: "Beginner", "Intermediate", "Advanced", "Expert" '
            "— omit if not stated\n"
            '- sourceRef: a short label indicating where this skill was found '
            "(omit if not found)\n\n"
            "--- education section ---\n"
            "An array of education objects extracted from the document. "
            "Each education object has these fields:\n"
            '- id: a unique slug for this education (e.g. "edu-mit-cs")\n'
            "- institution: the school or university name\n"
            '- degree: the degree or program name (e.g. "Bachelor of Science", '
            '"M.S. in Computer Science")\n'
            '- fieldOfStudy: the field or major (e.g. "Computer Science") '
            "— omit if not clear\n"
            '- startDate: start date (e.g. "2018-09", "2016", or full date)\n'
            '- endDate: end date, or null if still enrolled (e.g. "2022-06")\n'
            "- isCurrent: boolean, true if the person is currently enrolled\n"
            '- location: where the institution is located (omit if not found)\n'
            '- description: additional notes, honours, or activities '
            "(omit if not found)\n"
            '- sourceRef: a short label indicating where this data came from '
            "(omit if not found)\n\n"
            "Example of the exact JSON structure to return:\n"
            '{"person": {"id": "person-smith", "firstName": "Jane", '
            '"lastName": "Smith", "fullName": "Jane Smith", '
            '"email": "jane@example.com", "phone": "+1 555 0100", '
            '"location": "London, UK"}, "experiences": ['
            '{"id": "exp-acme", "organization": "ACME Inc.", '
            '"title": "Senior Engineer", "employmentType": "Full-time", '
            '"location": "London, UK", "startDate": "2020-01", "endDate": null, '
            '"isCurrent": true, "summary": "Led platform team.", '
            '"responsibilities": ["Lead delivery"], '
            '"achievements": ["Cut cost 20%"], '
            '"technologies": ["AWS", "Python"]}], '
            '"skills": [{"id": "skill-python", "name": "Python", '
            '"category": "Programming Language", "proficiency": "Expert"}], '
            '"education": [{"id": "edu-kth", "institution": "KTH Royal '
            'Institute of Technology", "degree": "M.S.", '
            '"fieldOfStudy": "Computer Science", "startDate": "2016-08", '
            '"endDate": "2018-06", "isCurrent": false}]}\n\n'
            "Use EXACTLY these key names. Do not invent different section or "
            "field names.\n\n"
            "Document text:\n"
            "---\n"
            f"{text}\n"
            "---\n"
            "Respond with valid JSON only. No markdown, no explanation."
        )
        return prompt

    def parse_response(self, response_text: str) -> dict[str, Any]:
        logger.debug(
            "Raw LLM response (%d chars):\n%s", len(response_text), response_text
        )
        cleaned = self._strip_code_fences(response_text)
        candidate, truncated = self._find_json_object(cleaned)
        if candidate is None:
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise LLMExtractionError(
                    "Failed to parse LLM response as JSON: no JSON object found "
                    f"in a response of {len(cleaned)} chars: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise LLMExtractionError("LLM response is not a JSON object")
            return data

        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", candidate))
            except json.JSONDecodeError:
                if truncated:
                    raise TruncatedResponseError(
                        "Failed to parse LLM response as JSON: response is "
                        "truncated mid-JSON (JSON object never closes; "
                        f"{len(candidate)} chars extracted, "
                        f"tail: ...{candidate[-120:]!r})."
                    ) from exc
                raise LLMExtractionError(
                    f"Failed to parse LLM response as JSON: {exc}\n"
                    f"Extracted JSON ({len(candidate)} chars):\n{candidate}"
                ) from exc
        if not isinstance(data, dict):
            raise LLMExtractionError("LLM response is not a JSON object")
        return data

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()

    @staticmethod
    def _find_json_object(text: str) -> tuple[str | None, bool]:
        """Locate the JSON object in ``text``.

        Returns ``(candidate, truncated)`` where ``candidate`` is the JSON
        object substring starting at the first ``{`` (``None`` when no ``{``
        exists), and ``truncated`` is True when the object never closes —
        the signature of a response cut off by an output/context limit.
        Surrounding prose and Markdown fences are ignored.
        """
        start = text.find("{")
        if start == -1:
            return None, False
        depth = 0
        in_string = False
        escaped = False
        i = start
        while i < len(text):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1], False
            i += 1
        return text[start:], True

    def to_person_data(self, data: dict[str, Any]) -> PersonData:
        person = data.get("person", data)
        if not isinstance(person, dict):
            person = {}
        return PersonData(
            id=person.get("id") or "person-unknown",
            first_name=person.get("firstName") or "",
            last_name=person.get("lastName") or "",
            full_name=person.get("fullName") or "",
            email=person.get("email"),
            phone=person.get("phone"),
            location=person.get("location"),
            linkedin=person.get("linkedin"),
            github=person.get("github"),
        )

    def to_experience_data(self, data: dict[str, Any]) -> list[ExperienceData]:
        raw = data.get("experiences", [])
        if not isinstance(raw, list):
            return []
        experiences: list[ExperienceData] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                continue
            experiences.append(
                ExperienceData(
                    id=entry.get("id") or f"exp-{i}",
                    organization=entry.get("organization") or "",
                    title=entry.get("title") or "",
                    employment_type=entry.get("employmentType"),
                    location=entry.get("location"),
                    start_date=entry.get("startDate"),
                    end_date=entry.get("endDate"),
                    is_current=entry.get("isCurrent"),
                    summary=entry.get("summary"),
                    responsibilities=entry.get("responsibilities") or [],
                    achievements=entry.get("achievements") or [],
                    technologies=entry.get("technologies") or [],
                    source_ref=entry.get("sourceRef"),
                )
            )
        return experiences

    def to_skill_data(self, data: dict[str, Any]) -> list[SkillData]:
        raw = data.get("skills", [])
        if not isinstance(raw, list):
            return []
        skills: list[SkillData] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                continue
            skills.append(
                SkillData(
                    name=entry.get("name") or "",
                    category=entry.get("category"),
                    proficiency=entry.get("proficiency"),
                    evidence=[],
                    confidence=1.0,
                    source_reference=entry.get("sourceRef"),
                )
            )
        return skills

    def to_education_data(self, data: dict[str, Any]) -> list[EducationData]:
        raw = data.get("education", [])
        if not isinstance(raw, list):
            return []
        education: list[EducationData] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                continue
            education.append(
                EducationData(
                    institution=entry.get("institution") or "",
                    degree=entry.get("degree") or "",
                    field_of_study=entry.get("fieldOfStudy"),
                    start_date=entry.get("startDate"),
                    end_date=entry.get("endDate"),
                    is_current=entry.get("isCurrent"),
                    location=entry.get("location"),
                    description=entry.get("description"),
                    confidence=1.0,
                    source_reference=entry.get("sourceRef"),
                )
            )
        return education

    @staticmethod
    def _rename_keys(entry: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
        renamed: dict[str, Any] = {}
        for key, value in entry.items():
            renamed[aliases.get(key, key)] = value
        return renamed

    @staticmethod
    def _split_duration(
        duration: str,
    ) -> tuple[str | None, str | None, bool]:
        """Split a natural-language duration into (start, end, is_current).

        Handles forms like ``"Sep 2022 - Present"``, ``"Feb 2015 - Feb 2019"``,
        and ``"2019 - 2021"``. Returns ``None`` values for unparseable parts.
        """
        parts = _DURATION_SPLIT_RE.split(duration.strip())
        start_raw = parts[0].strip()
        end_raw = parts[1].strip() if len(parts) > 1 else ""
        is_current = end_raw.lower().strip() in _CURRENT_WORDS

        def to_iso(raw: str) -> str | None:
            raw = raw.strip()
            month = _MONTH_YEAR_RE.match(raw)
            if month:
                month_num = _MONTH_NUMBERS.get(month.group("mon").lower()[:3])
                if month_num:
                    return f"{month.group('yr')}-{month_num:02d}"
                return month.group("yr")
            if _YEAR_RE.match(raw):
                return raw
            return None

        start = to_iso(start_raw) if start_raw else None
        end = None
        if end_raw and not is_current:
            end = to_iso(end_raw)
        return start, end, is_current

    def _normalize_experience(self, entry: dict[str, Any]) -> dict[str, Any]:
        entry = self._rename_keys(entry, _EXPERIENCE_FIELD_ALIASES)
        duration = entry.pop("Duration", None)
        if isinstance(duration, str) and "startDate" not in entry:
            start, end, is_current = self._split_duration(duration)
            if start:
                entry["startDate"] = start
            if end or is_current:
                entry["endDate"] = end
            if is_current or end:
                entry["isCurrent"] = is_current
        return entry

    def normalize_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Map alternate model schema keys onto the canonical extraction schema.

        Small local models occasionally ignore the requested key names and emit
        their own (e.g. ``PersonalDetails`` / ``WorkExperience``). This remaps
        those known variants so extraction still yields a valid profile.
        Canonical keys always win when both are present.
        """
        normalized: dict[str, Any] = {}
        for key, value in data.items():
            target = _TOP_LEVEL_ALIASES.get(key, key)
            if target != key and target in normalized:
                continue
            normalized[target] = value

        person = normalized.get("person")
        if isinstance(person, dict):
            normalized["person"] = self._rename_keys(person, _PERSON_FIELD_ALIASES)

        experiences = normalized.get("experiences")
        if isinstance(experiences, list):
            normalized["experiences"] = [
                self._normalize_experience(entry)
                for entry in experiences
                if isinstance(entry, dict)
            ]

        skills = normalized.get("skills")
        if isinstance(skills, list):
            normalized["skills"] = [
                self._rename_keys(entry, _SKILL_FIELD_ALIASES)
                for entry in skills
                if isinstance(entry, dict)
            ]

        education = normalized.get("education")
        if isinstance(education, list):
            normalized["education"] = [
                self._rename_keys(entry, _EDUCATION_FIELD_ALIASES)
                for entry in education
                if isinstance(entry, dict)
            ]

        return normalized

    def to_result(self, data: dict[str, Any]) -> ExtractionResult:
        data = self.normalize_response(data)
        return ExtractionResult(
            person=self.to_person_data(data),
            experiences=self.to_experience_data(data),
            skills=self.to_skill_data(data),
            education=self.to_education_data(data),
        )


class OpenAILLMExtractor(LLMExtractor):
    """Backward-compatible OpenAI extractor backed by the OpenAI provider adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        provider: OpenAIProvider | None = None,
        transport: Any | None = None,
    ) -> None:
        if provider is None:
            provider = OpenAIProvider(api_key=api_key, model=model, transport=transport)
        super().__init__(provider=provider)
        self.api_key = provider.api_key
        self.model = provider.model


class OllamaLLMExtractor(LLMExtractor):
    """Backward-compatible Ollama extractor backed by the local provider adapter."""

    extraction_timeout = float(
        os.environ.get("OLLAMA_EXTRACTION_TIMEOUT", "900.0")
    )

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        provider: OllamaProvider | None = None,
        transport: Any | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> None:
        if provider is None:
            provider = OllamaProvider(
                host=host, model=model, transport=transport, num_ctx=num_ctx, num_predict=num_predict
            )
        super().__init__(provider=provider)
        self.host = provider.host
        self.model = provider.model


def create_llm_extractor() -> LLMExtractor:
    provider = create_ai_provider()
    if isinstance(provider, OpenAIProvider):
        return OpenAILLMExtractor(provider=provider)
    if isinstance(provider, OllamaProvider):
        return OllamaLLMExtractor(provider=provider)
    return LLMExtractor(provider=provider)
