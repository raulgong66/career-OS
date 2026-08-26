"""Reusable CareerOS generation pipelines."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Union

from .evidence_selector import EvidenceSelector
from .export_contract import ExportContractBuilder
from .generators import GeneratorRegistry, default_generator_registry
from .interview import build_preparation_plan
from .reasoning import ReasoningFindings
from .optimizer import CVOptimizer, OptimizationResult
from .profile_loader import ProfileLoader
from .recommendation_applier import RecommendationApplier
from .schema_loader import SchemaLoader


def _run_reasoning(profile: dict) -> ReasoningFindings | None:
    """Run the deterministic Reasoning Engine on a profile exactly once per call.

    Returns ReasoningFindings (never None for valid profiles) or None on failure.
    """
    try:
        from careeros.reasoning import ReasoningEngine, ReasoningFindings, create_default_registry
        registry = create_default_registry()
        engine = ReasoningEngine(registry)
        report = engine.analyze(profile)
        return ReasoningFindings.from_report(report)
    except Exception:
        return None


def _infer_artifact_type(artifact: dict) -> str:
    """Infer artifact type from metadata when explicit artifactType is missing (legacy compat)."""
    explicit = artifact.get("artifactType")
    if explicit:
        return str(explicit).upper()
    art_id = str(artifact.get("id", "")).lower()
    title = str(artifact.get("title", "")).lower()
    if "interest" in art_id or "interest" in title:
        return "INTEREST_LETTER"
    if "cover" in art_id or "cover" in title:
        return "COVER_LETTER"
    if "interview" in art_id or "interview" in title:
        return "INTERVIEW_PREPARATION_GUIDE"
    if "cv" in art_id or "cv" in title or "resume" in art_id or "resume" in title:
        return "CV"
    return ""


def _ensure_interest_letter_context(profile: dict, contract) -> None:
    """Populate target_contexts for INTEREST_LETTER from profile when missing.

    The standard interest-letter template hardcodes targetContextRefs as empty,
    which causes the generator to skip JD-aware opening/closing paragraphs.
    When the profile carries target contexts, inject the first one so the
    generator can render role-aware content.
    """
    if contract.artifact_type.upper() != "INTEREST_LETTER":
        return
    if contract.target_contexts:
        return
    profile_contexts = profile.get("targetContexts", [])
    if profile_contexts:
        contract.target_contexts = [profile_contexts[0]]


def generate_artifact(
    profile_file: Union[str, Path],
    artifact_id: str,
    output_format: str,
    schema_loader: SchemaLoader,
    registry: Union[GeneratorRegistry, None] = None,
    job_description: Union[str, None] = None,
) -> Union[str, tuple[str, OptimizationResult]]:
    """Generate an artifact from a profile file, artifact id, and output format.
    
    Runs deterministic reasoning exactly once per request and attaches the
    findings to the ExportContract so generators can consume them.
    
    When job_description is provided for CV/Resume/Interest Letter artifacts,
    generates a tailored artifact with ADD recommendations applied and returns
    (artifact, OptimizationResult). For other artifact types (e.g. cover letters)
    the JD is passed through the contract for generator-level consumption.
    """
    generator_registry = registry or default_generator_registry()
    profile = ProfileLoader(schema_loader).load(profile_file)

    # Determine artifact type to decide the generation path
    artifacts = profile.get("artifacts", [])
    target_artifact = next((a for a in artifacts if a.get("id") == artifact_id), None)
    if target_artifact is None:
        from .exceptions import EntityNotFoundError
        raise EntityNotFoundError(f"Artifact not found: {artifact_id}")
    artifact_type = _infer_artifact_type(target_artifact)

    # CV/Resume/Interest Letter artifacts with JD → tailoring path (ADD recommendations)
    if job_description and artifact_type in {"CV", "RESUME", "INTEREST_LETTER"}:
        return generate_tailored_artifact(profile_file, artifact_id, output_format, job_description, schema_loader, registry)

    # All other artifacts (cover letters, etc.) → normal generation path
    findings = _run_reasoning(profile)
    contract = ExportContractBuilder(schema_loader).build(profile, artifact_id, validate=False, reasoning=findings)
    selected_contract = EvidenceSelector().select(contract)

    _ensure_interest_letter_context(profile, selected_contract)
    selected_contract.job_description = job_description

    if artifact_type == "INTERVIEW_PREPARATION_GUIDE":
        selected_contract.interview_plan = build_preparation_plan(
            profile, target_contexts=selected_contract.target_contexts
        )

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
) -> tuple[str, OptimizationResult]:
    """Generate a tailored artifact by applying ADD recommendations from job description analysis.

    Args:
        profile_file: Path to the profile file.
        artifact_id: ID of the artifact to tailor.
        output_format: Output format for the artifact.
        job_description: Optional job description text to prioritize recommendations.
        schema_loader: Schema loader instance.
        registry: Optional generator registry.

    Returns:
        Tuple of (generated artifact as string/bytes, OptimizationResult).
    """
    generator_registry = registry or default_generator_registry()
    profile = ProfileLoader(schema_loader).load(profile_file)

    # Generate recommendations
    optimizer = CVOptimizer(profile)
    optimization_result = optimizer.optimize_cv(artifact_id, job_description)

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
    tailored_artifact = applier.apply_add_recommendations(target_artifact, optimization_result.recommendations)

    # Replace the artifact in the profile with the tailored version
    tailored_profile = copy.deepcopy(profile)
    for i, art in enumerate(tailored_profile.get("artifacts", [])):
        if art.get("id") == artifact_id:
            tailored_profile["artifacts"][i] = tailored_artifact
            break

    # Run reasoning on the tailored profile (exactly once)
    tailored_findings = _run_reasoning(tailored_profile)

    # Generate the artifact using the tailored profile
    contract = ExportContractBuilder(schema_loader).build(tailored_profile, artifact_id, validate=False, reasoning=tailored_findings)
    selected_contract = EvidenceSelector().select(contract)
    _ensure_interest_letter_context(tailored_profile, selected_contract)
    selected_contract.job_description = job_description
    generator = generator_registry.resolve(selected_contract.artifact_type, output_format)
    artifact = generator.generate(selected_contract)
    
    return artifact, optimization_result
