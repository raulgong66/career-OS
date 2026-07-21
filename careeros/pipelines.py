"""Reusable CareerOS generation pipelines."""

from __future__ import annotations

from pathlib import Path

from .evidence_selector import EvidenceSelector
from .export_contract import ExportContractBuilder
from .generators import GeneratorRegistry, default_generator_registry
from .profile_loader import ProfileLoader
from .schema_loader import SchemaLoader


def generate_artifact(
    profile_file: str | Path,
    artifact_id: str,
    output_format: str,
    schema_loader: SchemaLoader,
    registry: GeneratorRegistry | None = None,
) -> str:
    """Generate an artifact from a profile file, artifact id, and output format."""
    generator_registry = registry or default_generator_registry()
    profile = ProfileLoader(schema_loader).load(profile_file)
    contract = ExportContractBuilder(schema_loader).build(profile, artifact_id, validate=False)
    selected_contract = EvidenceSelector().select(contract)
    generator = generator_registry.resolve(selected_contract.artifact_type, output_format)
    return generator.generate(selected_contract)


def generate_markdown_cv(profile_file: str | Path, artifact_id: str, schema_loader: SchemaLoader) -> str:
    """Generate a Markdown CV from a profile file and artifact id."""
    return generate_artifact(profile_file, artifact_id, "markdown", schema_loader)
