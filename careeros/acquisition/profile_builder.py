from __future__ import annotations

from typing import Any

from .builders import (
    BuilderContext,
    BuilderRegistry,
    EducationBuilder,
    ExperienceBuilder,
    PersonBuilder,
    SkillBuilder,
)
from .person_data import EducationData, ExperienceData, ExtractionResult, PersonData, SkillData


class CanonicalProfileBuilder:
    PROFILE_VERSION = "1.0.0"

    def __init__(self) -> None:
        self.registry = BuilderRegistry()
        self.registry.register(PersonData, PersonBuilder())
        self.registry.register(ExperienceData, ExperienceBuilder())
        self.registry.register(SkillData, SkillBuilder())
        self.registry.register(EducationData, EducationBuilder())

    def normalize(self, result: ExtractionResult) -> ExtractionResult:
        data_by_type: dict[type, list] = {}
        for entity_type, builder in self.registry.all():
            raw = getattr(result, builder.extraction_field, [])
            if builder.singular:
                raw = [raw]
            data_by_type[entity_type] = builder.normalize(raw)

        for entity_type, builder in self.registry.all():
            if entity_type in data_by_type:
                data_by_type[entity_type] = builder.prepare(
                    data_by_type[entity_type], data_by_type
                )

        kwargs: dict[str, Any] = {
            f.name: getattr(result, f.name)
            for f in ExtractionResult.__dataclass_fields__.values()
        }

        for entity_type, builder in self.registry.all():
            if entity_type in data_by_type:
                items = data_by_type[entity_type]
                kwargs[builder.extraction_field] = items[0] if builder.singular else items

        return ExtractionResult(**kwargs)

    def build(
        self,
        person: PersonData,
        experiences: list[ExperienceData] | None = None,
        skills: list[SkillData] | None = None,
        education: list[EducationData] | None = None,
        source_document: str | None = None,
        extraction_timestamp: str | None = None,
        source_name: str | None = None,
        source_hash: str | None = None,
        imported_at: str | None = None,
    ) -> dict[str, Any]:
        context = BuilderContext()

        data_by_type: dict[type, list] = {
            PersonData: [person],
            ExperienceData: experiences or [],
            SkillData: skills or [],
            EducationData: education or [],
        }

        for entity_type, builder in self.registry.all():
            if entity_type in data_by_type:
                data_by_type[entity_type] = builder.normalize(
                    data_by_type[entity_type]
                )

        for entity_type, builder in self.registry.all():
            if entity_type in data_by_type:
                data_by_type[entity_type] = builder.prepare(
                    data_by_type[entity_type], data_by_type
                )

        profile: dict[str, Any] = {
            "profileVersion": self.PROFILE_VERSION,
            "person": {},
            "professionalSummaries": [],
            "experiences": [],
            "organizations": [],
            "projects": [],
            "skills": [],
            "achievements": [],
            "evidence": [],
            "education": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
            "extensions": {},
        }

        for entity_type, builder in self.registry.all():
            if entity_type in data_by_type:
                result = builder.build_many(data_by_type[entity_type], context)
                if builder.singular:
                    profile[builder.profile_key] = result[0] if result else {}
                else:
                    profile[builder.profile_key] = result

        profile["organizations"] = self._organizations_from_context(context)

        trace: dict[str, str] = {}
        if source_name:
            trace["sourceName"] = source_name
        if source_hash:
            trace["sourceHash"] = source_hash
        if source_document:
            trace["sourceDocument"] = source_document
        if extraction_timestamp:
            trace["extractionTimestamp"] = extraction_timestamp
        if imported_at:
            trace["importedAt"] = imported_at
        if trace:
            profile["extensions"]["_acquisition"] = trace
        if imported_at:
            profile["extensions"]["importedAt"] = imported_at
        return profile

    @staticmethod
    def _organizations_from_context(context: BuilderContext) -> list[dict[str, Any]]:
        orgs: list[dict[str, Any]] = []
        for norm_key, oid in context.organization_id_map.items():
            orgs.append({
                "id": oid,
                "name": context.organization_names.get(norm_key, ""),
            })
        return orgs
