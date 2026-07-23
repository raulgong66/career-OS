"""Reusable CareerOS generation pipelines."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Union

from .evidence_selector import EvidenceSelector
from .export_contract import ExportContractBuilder
from .generators import GeneratorRegistry, default_generator_registry
from .optimizer import CVOptimizer
from .profile_loader import ProfileLoader
from .recommendation_applier import RecommendationApplier
from .schema_loader import SchemaLoader


def generate_artifact(
    profile_file: Union[str, Path],
    artifact_id: str,
    output_format: str,
    schema_loader: SchemaLoader,
    registry: Union[GeneratorRegistry, None] = None,
) -> str:
    """Generate an artifact from a profile file, artifact id, and output format."""
    generator_registry = registry or default_generator_registry()
    profile = ProfileLoader(schema_loader).load(profile_file)
    contract = ExportContractBuilder(schema_loader).build(profile, artifact_id, validate=False)
    selected_contract = EvidenceSelector().select(contract)
    generator = generator_registry.resolve(selected_contract.artifact_type, output_format)
    return generator.generate(selected_contract)


def generate_markdown_cv(profile_file: Union[str, Path], artifact_id: str, schema_loader: SchemaLoader) -> str:
    """Generate a Markdown CV from a profile file and artifact id."""
    return generate_artifact(profile_file, artifact_id, "markdown", schema_loader)


def generate_tailored_artifact(
    profile_file: Union[str, Path],
    artifact_id: str,
    output_format: str,
    job_description: Union[str, None],
    schema_loader: SchemaLoader,
    registry: Union[GeneratorRegistry, None] = None,
) -> str:
    """Generate a tailored artifact by applying ADD recommendations from job description analysis.

    Args:
        profile_file: Path to the profile file.
        artifact_id: ID of the artifact to tailor.
        output_format: Output format for the artifact.
        job_description: Optional job description text to prioritize recommendations.
        schema_loader: Schema loader instance.
        registry: Optional generator registry.

    Returns:
        The generated artifact as a string or bytes.
    """
    generator_registry = registry or default_generator_registry()
    profile = ProfileLoader(schema_loader).load(profile_file)

    # Generate recommendations
    optimizer = CVOptimizer(profile)
    recommendations = optimizer.optimize_cv(artifact_id, job_description)

    # Find the target artifact
    artifacts = profile.get("artifacts", [])
    target_artifact = None
    for art in artifacts:
        if art.get("id") == artifact_id:
            target_artifact = art
            break

    if not target_artifact:
        from .exceptions import EntityNotFoundError
        raise EntityNotFoundError(f"Artifact not found: {artifact_id}")

    # Apply ADD recommendations to create tailored artifact
    applier = RecommendationApplier()
    tailored_artifact = applier.apply_add_recommendations(target_artifact, recommendations)

    # Replace the artifact in the profile with the tailored version
    tailored_profile = copy.deepcopy(profile)
    for i, art in enumerate(tailored_profile.get("artifacts", [])):
        if art.get("id") == artifact_id:
            tailored_profile["artifacts"][i] = tailored_artifact
            break

    # Generate the artifact using the tailored profile
    contract = ExportContractBuilder(schema_loader).build(tailored_profile, artifact_id, validate=False)
    selected_contract = EvidenceSelector().select(contract)
    generator = generator_registry.resolve(selected_contract.artifact_type, output_format)
    return generator.generate(selected_contract)
