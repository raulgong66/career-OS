"""Canonical export contract for downstream generators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .exceptions import EntityNotFoundError, ValidationError
from .schema_loader import SchemaLoader
from .validator import EntityValidator

if TYPE_CHECKING:
    from .interview.domain import InterviewPlan


_SOURCE_COLLECTIONS = {
    "achievement": "achievements",
    "artifact": "artifacts",
    "certification": "certifications",
    "education": "education",
    "evidence": "evidence",
    "experience": "experiences",
    "organization": "organizations",
    "person": "person",
    "professional_summary": "professionalSummaries",
    "professionalsummary": "professionalSummaries",
    "project": "projects",
    "skill": "skills",
}


@dataclass
class ExportSource:
    """A resolved canonical profile element selected for export."""

    type: str
    id: str
    data: dict[str, Any]
    ref: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the source to a serializable dictionary."""
        return {"type": self.type, "id": self.id, "data": self.data, "ref": self.ref}


from .reasoning import ReasoningFindings


@dataclass
class ExportContract:
    """Provider-agnostic input contract for generated career artifacts."""

    profile_version: str
    artifact_id: str
    artifact_type: str
    person: dict[str, Any]
    artifact: dict[str, Any]
    target_contexts: list[dict[str, Any]] = field(default_factory=list)
    sources: list[ExportSource] = field(default_factory=list)
    reasoning: ReasoningFindings | None = field(default=None, compare=False)
    job_description: str | None = None
    interview_plan: "InterviewPlan | None" = field(default=None, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert the contract to a serializable dictionary."""
        return {
            "profileVersion": self.profile_version,
            "artifactId": self.artifact_id,
            "artifactType": self.artifact_type,
            "person": self.person,
            "artifact": self.artifact,
            "targetContexts": self.target_contexts,
            "sources": [source.to_dict() for source in self.sources],
        }


class ExportContractBuilder:
    """Build generator-ready export contracts from canonical profile data."""

    def __init__(self, schema_loader: SchemaLoader) -> None:
        """Create a builder bound to the existing profile schema."""
        self.validator = EntityValidator(schema_loader)

    def build(
        self,
        profile: dict[str, Any],
        artifact_id: str,
        *,
        validate: bool = True,
        reasoning: ReasoningFindings | None = None,
    ) -> ExportContract:
        """Build an export contract for a profile artifact.

        Args:
            profile: Canonical profile payload.
            artifact_id: Identifier of the artifact to export.
            validate: Whether to validate the profile against the existing schema.
            reasoning: Optional ReasoningFindings from the deterministic Reasoning Engine.

        Returns:
            A provider-agnostic export contract.

        Raises:
            EntityNotFoundError: If the artifact or one of its references cannot be resolved.
            ValidationError: If profile validation fails.
        """
        if validate:
            result = self.validator.validate_entity(profile, "profile")
            if not result.is_valid:
                raise ValidationError("Profile validation failed", errors=result.errors)

        artifact = self._find_by_id(profile.get("artifacts", []), artifact_id)
        if artifact is None:
            raise EntityNotFoundError(f"Artifact not found: {artifact_id}")

        target_contexts = self._resolve_target_contexts(profile, artifact.get("targetContextRefs", []))
        sources = self._resolve_sources(profile, artifact.get("sourceRefs", []))

        def _infer_type(a: dict) -> str:
            explicit = a.get("artifactType")
            if explicit:
                return str(explicit)
            a_id = str(a.get("id", "")).lower()
            a_title = str(a.get("title", "")).lower()
            if "interest" in a_id or "interest" in a_title:
                return "INTEREST_LETTER"
            if "cover" in a_id or "cover" in a_title:
                return "COVER_LETTER"
            if "interview" in a_id or "interview" in a_title:
                return "INTERVIEW_PREPARATION_GUIDE"
            if "cv" in a_id or "cv" in a_title or "resume" in a_id or "resume" in a_title:
                return "CV"
            return ""

        return ExportContract(
            profile_version=str(profile.get("profileVersion", "")),
            artifact_id=artifact_id,
            artifact_type=_infer_type(artifact),
            person=profile.get("person", {}),
            artifact=artifact,
            target_contexts=target_contexts,
            sources=sources,
            reasoning=reasoning,
        )

    def _resolve_target_contexts(self, profile: dict[str, Any], refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve target-context references from the profile."""
        contexts = profile.get("targetContexts", [])
        resolved = []
        for ref in refs:
            context_id = ref.get("id")
            context = self._find_by_id(contexts, context_id)
            if context is None:
                raise EntityNotFoundError(f"Target context not found: {context_id}")
            resolved.append(context)
        return resolved

    def _resolve_sources(self, profile: dict[str, Any], refs: list[dict[str, Any]]) -> list[ExportSource]:
        """Resolve source references from the profile."""
        resolved = []
        for ref in refs:
            source_id = ref.get("id")
            source_type = str(ref.get("type", "")).strip()
            source = self._resolve_source(profile, source_type, source_id)
            if source is None:
                raise EntityNotFoundError(f"Source not found: {source_type}/{source_id}")
            resolved.append(ExportSource(type=source_type, id=str(source_id), data=source, ref=ref))
        return resolved

    def _resolve_source(self, profile: dict[str, Any], source_type: str, source_id: Any) -> dict[str, Any] | None:
        """Resolve a single source reference by type and identifier."""
        collection_name = _SOURCE_COLLECTIONS.get(source_type.lower())
        if collection_name is None:
            raise EntityNotFoundError(f"Unsupported source type: {source_type}")

        collection = profile.get(collection_name)
        if collection_name == "person":
            person = collection if isinstance(collection, dict) else {}
            return person if person.get("id") == source_id else None

        return self._find_by_id(collection or [], source_id)

    @staticmethod
    def _find_by_id(items: list[dict[str, Any]], item_id: Any) -> dict[str, Any] | None:
        """Find a dictionary item by its stable id."""
        for item in items:
            if item.get("id") == item_id:
                return item
        return None
