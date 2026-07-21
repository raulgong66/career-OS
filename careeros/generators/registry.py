"""Generator registry for artifact rendering."""

from __future__ import annotations

from typing import Protocol

from ..exceptions import ValidationError
from ..export_contract import ExportContract
from .docx_cv import DocxCVGenerator
from .markdown_cover_letter import MarkdownCoverLetterGenerator
from .markdown_cv import MarkdownCVGenerator


class ArtifactGenerator(Protocol):
    """Protocol implemented by artifact generators."""

    def generate(self, contract: ExportContract) -> str | bytes:
        """Generate an artifact from an export contract."""
        ...


class GeneratorRegistry:
    """Resolve generators by artifact type and output format."""

    def __init__(self) -> None:
        """Create an empty generator registry."""
        self._generators: dict[tuple[str, str], ArtifactGenerator] = {}

    def register(self, artifact_type: str, output_format: str, generator: ArtifactGenerator) -> None:
        """Register a generator for an artifact type and output format."""
        self._generators[self._key(artifact_type, output_format)] = generator

    def resolve(self, artifact_type: str, output_format: str) -> ArtifactGenerator:
        """Resolve a registered generator."""
        key = self._key(artifact_type, output_format)
        try:
            return self._generators[key]
        except KeyError as exc:
            raise ValidationError(f"No generator registered for {artifact_type}/{output_format}") from exc

    @staticmethod
    def _key(artifact_type: str, output_format: str) -> tuple[str, str]:
        """Normalize a registry key."""
        return (artifact_type.strip().upper(), output_format.strip().lower())


def default_generator_registry() -> GeneratorRegistry:
    """Create the default registry for implemented generators."""
    registry = GeneratorRegistry()
    markdown_cv_generator = MarkdownCVGenerator()
    markdown_cover_letter_generator = MarkdownCoverLetterGenerator()
    docx_cv_generator = DocxCVGenerator()
    registry.register("CV", "markdown", markdown_cv_generator)
    registry.register("RESUME", "markdown", markdown_cv_generator)
    registry.register("CV", "docx", docx_cv_generator)
    registry.register("RESUME", "docx", docx_cv_generator)
    registry.register("COVER_LETTER", "markdown", markdown_cover_letter_generator)
    return registry
