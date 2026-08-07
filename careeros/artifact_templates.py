from __future__ import annotations

from typing import Any, Protocol


_ENTITY_MAPPINGS: list[tuple[str, str]] = [
    ("professional_summary", "professionalSummaries"),
    ("experience", "experiences"),
    ("skill", "skills"),
    ("education", "education"),
    ("certification", "certifications"),
    ("project", "projects"),
    ("achievement", "achievements"),
]


class ArtifactTemplate(Protocol):
    template_id: str
    display_name: str
    artifact_type: str

    def build(self, profile: dict[str, Any], title: str | None = None) -> dict[str, Any]: ...

    def preview(self, profile: dict[str, Any]) -> str:
        """Render the template against a profile as markdown without side effects.

        Fastest path: reuses ExportContractBuilder + EvidenceSelector +
        GeneratorRegistry and skips reasoning re-run, JD processing, and any
        persistence. Must never create an artifact record or mutate the profile.
        """


def _render_preview(template: ArtifactTemplate, profile: dict[str, Any]) -> str:
    """Render a template preview through the canonical generation pipeline.

    Uses a deep copy of the profile with a virtual artifact appended so the
    existing ExportContractBuilder can resolve sources without ever mutating or
    persisting anything. Skips reasoning re-run and target-context filtering.
    """
    from copy import deepcopy

    from .evidence_selector import EvidenceSelector
    from .export_contract import ExportContractBuilder
    from .generators import default_generator_registry
    from .schema_loader import SchemaLoader

    virtual_artifact = template.build(profile, title="Preview")

    preview_profile = deepcopy(profile)
    artifacts = preview_profile.get("artifacts", [])
    artifacts.append(virtual_artifact)
    preview_profile["artifacts"] = artifacts

    contract = ExportContractBuilder(SchemaLoader()).build(
        preview_profile,
        virtual_artifact["id"],
        validate=False,
        reasoning=None,
    )
    selected = EvidenceSelector().select(contract)
    generator = default_generator_registry().resolve(template.artifact_type, "markdown")
    return generator.generate(selected)


class StandardCVTemplate:
    template_id = "standard_cv"
    display_name = "Tailored CV"
    artifact_type = "CV"

    def preview(self, profile: dict[str, Any]) -> str:
        """Render a render-only markdown preview of this template."""
        return _render_preview(self, profile)

    def build(self, profile: dict[str, Any], title: str | None = None) -> dict[str, Any]:
        source_refs: list[dict[str, str]] = []
        for ref_type, field in _ENTITY_MAPPINGS:
            for entity in profile.get(field, []):
                if entity.get("id"):
                    source_refs.append({"id": entity["id"], "type": ref_type})

        person = profile.get("person", {})
        person_id = person.get("id", "unknown")

        return {
            "id": f"artf-{self.template_id}-{person_id}",
            "title": title or self.display_name,
            "artifactType": self.artifact_type,
            "sourceRefs": source_refs,
            "targetContextRefs": [],
            "derivedFromProfileVersion": profile.get("profileVersion", "1.0.0"),
        }


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, ArtifactTemplate] = {}

    def register(self, template: ArtifactTemplate) -> None:
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> ArtifactTemplate:
        template = self._templates.get(template_id)
        if template is None:
            raise KeyError(f"Unknown artifact template: {template_id}")
        return template

    def list(self) -> list[dict[str, str]]:
        return [
            {
                "id": t.template_id,
                "displayName": t.display_name,
                "artifactType": t.artifact_type,
            }
            for t in self._templates.values()
        ]


class StandardInterestLetterTemplate:
    template_id = "standard_interest_letter"
    display_name = "Interest Letter"
    artifact_type = "INTEREST_LETTER"

    def preview(self, profile: dict[str, Any]) -> str:
        """Render a render-only markdown preview of this template."""
        return _render_preview(self, profile)

    _interest_letter_mappings: list[tuple[str, str]] = [
        ("professional_summary", "professionalSummaries"),
        ("experience", "experiences"),
        ("skill", "skills"),
        ("education", "education"),
    ]

    def build(self, profile: dict[str, Any], title: str | None = None) -> dict[str, Any]:
        source_refs: list[dict[str, str]] = []
        for ref_type, field in self._interest_letter_mappings:
            for entity in profile.get(field, []):
                if entity.get("id"):
                    source_refs.append({"id": entity["id"], "type": ref_type})

        person = profile.get("person", {})
        person_id = person.get("id", "unknown")

        return {
            "id": f"artf-{self.template_id}-{person_id}",
            "title": title or self.display_name,
            "artifactType": self.artifact_type,
            "sourceRefs": source_refs,
            "targetContextRefs": [],
            "derivedFromProfileVersion": profile.get("profileVersion", "1.0.0"),
        }


_default_registry: TemplateRegistry | None = None


def default_template_registry() -> TemplateRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = TemplateRegistry()
        _default_registry.register(StandardCVTemplate())
        _default_registry.register(StandardInterestLetterTemplate())
    return _default_registry
