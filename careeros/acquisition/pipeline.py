from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from careeros.exceptions import CareerOSException
from careeros.schema_loader import SchemaLoader
from careeros.validator import EntityValidator

from .document_reader import DocumentReader
from .llm_extractor import LLMExtractor, create_llm_extractor
from .person_data import ExtractionResult
from .profile_builder import CanonicalProfileBuilder
from .text_extractor import TextExtractor
from .yaml_writer import YamlWriter


ReviewHookFn = Callable[[ExtractionResult], ExtractionResult]


class PipelineError(CareerOSException):
    pass


class AcquisitionPipeline:
    def __init__(
        self,
        document_reader: DocumentReader | None = None,
        text_extractor: TextExtractor | None = None,
        llm_extractor: LLMExtractor | None = None,
        profile_builder: CanonicalProfileBuilder | None = None,
        yaml_writer: YamlWriter | None = None,
        review_callback: ReviewHookFn | None = None,
    ) -> None:
        self.document_reader = document_reader or DocumentReader()
        self.text_extractor = text_extractor or TextExtractor()
        self.llm_extractor = llm_extractor
        self.profile_builder = profile_builder or CanonicalProfileBuilder()
        self.yaml_writer = yaml_writer or YamlWriter()
        # review_callback is a pass-through hook by default.
        # When Human Review is implemented, inject a callback that
        # presents the normalized result for review and returns
        # the reviewed (possibly corrected) result.
        self.review_callback = review_callback or self._pass_through

    @staticmethod
    def _pass_through(result: ExtractionResult) -> ExtractionResult:
        return result

    def run(
        self,
        source_path: str | Path,
        output_path: str | Path | None = None,
        schema: dict[str, Any] | None = None,
    ) -> Path:
        # 1. Read — parse the source document into raw text
        raw_text = self.document_reader.read(source_path)

        # 2. Extract — clean the text for LLM consumption
        cleaned_text = self.text_extractor.extract(raw_text)

        if self.llm_extractor is None:
            self.llm_extractor = self._default_llm_extractor()

        # 3. Extract — LLM extraction produces structured entities
        result: ExtractionResult = self.llm_extractor.extract(cleaned_text, schema)
        result.source_document = str(source_path)
        result.extraction_timestamp = datetime.now(timezone.utc).isoformat()

        # 4. Normalize — deduplicate, sort, clean extracted data
        normalized = self.profile_builder.normalize(result)

        # 5. Review Hook — pass-through until Human Review is implemented.
        #    The reviewer receives the normalized result and can modify
        #    entities before profile assembly.
        reviewed = self.review_callback(normalized)

        # 6. Build — assemble the canonical profile dict from entities
        profile = self.profile_builder.build(
            reviewed.person,
            experiences=reviewed.experiences,
            skills=reviewed.skills,
            education=reviewed.education,
            source_document=reviewed.source_document,
            extraction_timestamp=reviewed.extraction_timestamp,
        )

        # 7. Validate — ensure the profile satisfies the canonical schema
        self._validate(profile)

        # 8. Write — persist the profile YAML
        written = self.yaml_writer.write(profile, output_path)
        return written

    def _validate(self, profile: dict[str, Any]) -> None:
        if not self._has_usable_content(profile):
            raise PipelineError(
                "No profile content could be extracted from the document."
            )
        try:
            from careeros.schema_loader import SchemaLoader
            from careeros.validator import EntityValidator

            loader = SchemaLoader()
            validator = EntityValidator(loader)
            result = validator.validate_entity(profile, "profile")
            if not result.is_valid:
                errors = "; ".join(
                    f"{e['path']}: {e['message']}" for e in result.errors
                )
                raise PipelineError(f"Generated profile failed validation: {errors}")
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(f"Validation error: {exc}") from exc

    @staticmethod
    def _has_usable_content(profile: dict[str, Any]) -> bool:
        person = profile.get("person", {}) or {}
        names = person.get("names") if isinstance(person, dict) else None
        has_person_name = any(
            isinstance(name, dict) and (name.get("value") or name.get("label"))
            for name in (names or [])
        )
        return bool(
            has_person_name
            or profile.get("experiences")
            or profile.get("skills")
            or profile.get("education")
            or profile.get("organizations")
        )

    @staticmethod
    def _default_llm_extractor() -> LLMExtractor:
        return create_llm_extractor()
