from __future__ import annotations

import json
from typing import Any

from careeros.exceptions import CareerOSException, LLMConfigurationError

from careeros.ai import AIError, AIProvider, create_ai_provider
from careeros.ai.ollama_provider import OllamaProvider
from careeros.ai.openai_provider import OpenAIProvider

from .person_data import EducationData, ExperienceData, ExtractionResult, PersonData, SkillData


class LLMExtractionError(CareerOSException):
    pass


class LLMExtractor:
    """Acquisition-domain service: extract structured profile data via an AI provider.

    Prompt construction and response parsing are business logic and stay here.
    The provider (an ``AIProvider``) only supplies the ``generate`` capability.
    """

    extraction_temperature = 0.1
    extraction_timeout = 60.0

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

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
            )
        except AIError as exc:
            raise LLMExtractionError(f"LLM call failed: {exc}") from exc

    def extract(
        self, text: str, schema: dict[str, Any] | None = None
    ) -> ExtractionResult:
        prompt = self.build_prompt(text, schema)
        response = self._complete(prompt)
        data = self.parse_response(response)
        return self.to_result(data)

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
            "Document text:\n"
            "---\n"
            f"{text}\n"
            "---\n"
            "Respond with valid JSON only. No markdown, no explanation."
        )
        return prompt

    def parse_response(self, response_text: str) -> dict[str, Any]:
        import re
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
                data = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise LLMExtractionError(
                    f"Failed to parse LLM response as JSON: {exc}\nResponse was:\n{response_text}"
                ) from exc
        if not isinstance(data, dict):
            raise LLMExtractionError("LLM response is not a JSON object")
        return data

    def to_person_data(self, data: dict[str, Any]) -> PersonData:
        person = data.get("person", data)
        return PersonData(
            id=person.get("id", "person-unknown"),
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
                    id=entry.get("id", f"exp-{i}"),
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

    def to_result(self, data: dict[str, Any]) -> ExtractionResult:
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

    extraction_timeout = 300.0

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        provider: OllamaProvider | None = None,
        transport: Any | None = None,
    ) -> None:
        if provider is None:
            provider = OllamaProvider(host=host, model=model, transport=transport)
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
