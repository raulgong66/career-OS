"""FastAPI application for CareerOS."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import yaml


from .runtime_config import (
    BACKEND_VERSION,
    RuntimeConfigurationError,
    print_configuration_banner,
    validate_runtime_config,
)

from careeros.csks.api import CSKS_ROUTER
from .routes.mission import MISSION_ROUTER
from .routes.profile_quality import PROFILE_QUALITY_ROUTER

try:
    runtime_config = validate_runtime_config()
except RuntimeConfigurationError as exc:
    print(f"CareerOS startup aborted: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
print_configuration_banner(runtime_config)

from careeros import CVOptimizer, EntityValidator, FileSystemRepository, OptimizationResult, OptimizationStatus, ProfileLoader, SchemaLoader, TemplateRegistry, default_template_registry, generate_artifact, generate_markdown_cv, run_profile_quality
from careeros.exceptions import CareerOSException, DuplicateProfileError, EntityNotFoundError, RepositoryError, SchemaLoadError, ValidationError
from careeros.acquisition import AcquisitionPipeline, DocumentReadError, LLMExtractionError, PipelineError
from careeros.import_classification import (
    CandidateMatch,
    ImportClassification,
    SAME_DOCUMENT,
    classify_import,
    retain_source,
    source_hash_for_bytes,
)
from careeros.profile_repository import ProfileRecord, ProfileRepository, ProfileState
from careeros.interview import InterviewEngine
from careeros.interview.exceptions import InvalidProfileError
from careeros.interview.simulation import (
    EvaluationEngine,
    InterviewAnswer,
    InterviewSession,
    InterviewSessionState,
    SessionEngine,
)
from careeros.interview.simulation.exceptions import (
    InterviewSimulationError,
    InvalidAnswerError,
    InvalidQuestionError,
    InvalidSessionStateError,
    MissingEvidenceReferenceError,
    NoActiveQuestionError,
)

from .interview_dto import to_session_response

from .dto import to_import_response, to_profile_details, to_profile_summary
from careeros.reasoning.rules.recommendation_rules import TECHNOLOGY_KEYWORDS
from careeros.resolution import (
    AchievementNotMeasurableError,
    EmptySummaryError,
    InvalidAchievementError,
    RESOLVABLE_RULES,
    ResolutionTargetNotFoundError,
    UnsupportedRuleError,
    _ARTIFACT_STATUS_CURRENT,
    apply_resolution,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

app = FastAPI(title="CareerOS API", version=BACKEND_VERSION)
app.include_router(CSKS_ROUTER)
app.include_router(MISSION_ROUTER)
app.include_router(PROFILE_QUALITY_ROUTER)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Optimization-Status",
        "X-Optimization-Message",
        "X-Optimization-Summary",
        "X-Recommendations",
    ],
)
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schemas"
PROFILES_ROOT = REPO_ROOT / "profiles"
PROFILE_REPOSITORY = ProfileRepository(PROFILES_ROOT)
SCHEMA_LOADER = SchemaLoader(SCHEMA_ROOT)
VALIDATOR = EntityValidator(SCHEMA_LOADER)
REPOSITORY = FileSystemRepository(REPO_ROOT / "data", SCHEMA_LOADER)


class HealthResponse(BaseModel):
    """Response model for health checks."""

    status: str = Field(description="Service health status.")


class VersionResponse(BaseModel):
    """Response model for version information."""

    version: str = Field(description="Service version.")


class SchemaInfoResponse(BaseModel):
    """Response model for schema metadata."""

    title: str
    description: str
    version: str


class ValidationRequest(BaseModel):
    """Request payload for validation."""

    payload: dict[str, Any]


class SearchRequest(BaseModel):
    """Request payload for entity search."""

    field: str
    value: str


class MarkdownCVRequest(BaseModel):
    """Request payload for Markdown CV generation."""

    profile_id: Optional[str] = Field(None, description="Profile identifier (filename without extension). Preferred over profile_path.")
    profile_path: Optional[Path] = Field(None, description="Deprecated: use profile_id instead.")
    artifact_id: str


class GenerateArtifactRequest(BaseModel):
    """Request payload for generic artifact generation."""

    profile_id: Optional[str] = Field(None, description="Profile identifier (filename without extension). Preferred over profile_path.")
    profile_path: Optional[Path] = Field(None, description="Deprecated: use profile_id instead.")
    artifact_id: str
    output_format: str
    job_description: Optional[str] = Field(None, description="Optional job description text to generate tailored artifact with recommendations.")


class OptimizeCVRequest(BaseModel):
    """Request payload for CV optimization recommendations."""

    profile: dict[str, Any] = Field(..., description="The complete canonical profile payload.")
    artifact_id: str = Field(..., description="ID of the CV artifact to optimize.")
    job_description: Optional[str] = Field(None, description="Optional job description text to prioritize recommendations.")


class EntityResponse(BaseModel):
    """Response model for persisted entities."""

    entity_type: str
    id: str
    data: dict[str, Any]


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    detail: str


class ProfileInfo(BaseModel):
    """Metadata for an available profile."""

    id: str = Field(description="Profile identifier (filename without extension).")
    name: str = Field(description="Human-readable profile name.")
    artifactCount: int = Field(description="Number of artifacts defined in the profile.")
    artifactIds: list[str] = Field(description="IDs of artifacts defined in the profile.")
    headline: str = Field(default="", description="Professional headline.")
    importedAt: str = Field(default="", description="ISO 8601 import timestamp.")
    state: str = Field(default="canonical", description="Current profile state (staging, canonical, archived).")


class ImportCandidate(BaseModel):
    """An existing profile that deterministically matched a new import."""

    profileId: str = Field(description="Identifier of the existing profile that matched.")
    matchedOn: list[str] = Field(default_factory=list, description="Deterministic signals that matched (sourceHash, name, name-tokens, email, phone, linkedin, github).")
    conflictingOn: list[str] = Field(default_factory=list, description="Deterministic signals that conflict (email, phone).")


class ImportClassificationInfo(BaseModel):
    """Deterministic Phase 2A import classification (never merges or promotes)."""

    result: str = Field(description="NEW_PERSON, SAME_DOCUMENT, POSSIBLE_SAME_PERSON, or IDENTITY_CONFLICT.")
    candidates: list[ImportCandidate] = Field(default_factory=list, description="Existing profiles matched as candidates.")


class ImportResponse(BaseModel):
    """Response after a successful profile import."""

    profileId: str = Field(description="Identifier of the imported profile.")
    profile: ProfileInfo = Field(description="Profile summary DTO.")
    classification: ImportClassificationInfo | None = Field(default=None, description="Deterministic Phase 2A import classification.")


class AnalyzeRequest(BaseModel):
    """Request payload for profile analysis."""

    profileId: str = Field(description="Profile identifier (filename without extension).")
    parameters: dict[str, Any] | None = Field(default=None, description="Optional analysis parameters and filters.")


class ApiErrorResponse(BaseModel):
    """Consistent error response across the Profile Management API."""

    error: str = Field(description="Machine-readable error code.")
    detail: str = Field(description="Human-readable description.")
    processingErrors: list[str] | None = Field(default=None, description="Optional list of processing errors.")


class CreateArtifactRequest(BaseModel):
    """Request payload for creating an artifact from a template."""

    template: str = Field(description="Template identifier (e.g. 'standard_cv').")
    title: str | None = Field(default=None, description="Optional human-readable artifact title.")


class TemplatePreviewRequest(BaseModel):
    """Request payload for rendering a template preview."""

    profile_id: str = Field(description="Profile identifier (filename without extension).")


class CreateArtifactResponse(BaseModel):
    """Response after creating an artifact."""

    artifactId: str = Field(description="ID of the created artifact.")
    artifact: dict[str, Any] = Field(description="The full artifact definition.")


class ResolveRecommendationRequest(BaseModel):
    """Request payload for guided recommendation resolution.

    Carries only the rule type, the target element, and the user's selections.
    No free-form payloads: the server applies the exact canonical edit for the
    rule type and persists it to the canonical profile.
    """

    triggeredRule: str = Field(description="Rule class name that produced the recommendation.")
    elementId: str = Field(description="ID of the profile element the resolution targets.")
    skillIds: list[str] = Field(default_factory=list, description="Selected skill references (project tagging / technologies / achievement skills).")
    experienceIds: list[str] = Field(default_factory=list, description="Selected experience references (project / skill evidence).")
    technologies: list[str] = Field(default_factory=list, description="Technology tags to attach to an experience.")
    achievementStatement: str = Field(default="", description="Measurable achievement statement to persist (NoMeasurableAchievementRule).")
    summaryText: str = Field(default="", description="Professional summary text to persist (GenericSummaryRule).")


class RegenerateArtifactRequest(BaseModel):
    """Request payload for explicitly regenerating a stale artifact.

    Regeneration always rebuilds the ExportContract from the canonical profile
    through the existing generation pipeline. It never mutates previously
    generated markdown/docx directly.
    """

    output_format: str = Field(default="markdown", description="Output format to regenerate (markdown or docx).")
    job_description: Optional[str] = Field(default=None, description="Optional job description to reproduce a tailored artifact.")


class EvidenceReferenceRequest(BaseModel):
    """A single ADR-002 evidence reference ``{id, type}``."""

    id: str = Field(description="Canonical element identifier.")
    type: str = Field(description="Canonical element type (experience, skill, ...).")


class CreateInterviewSessionRequest(BaseModel):
    """Request payload for creating an interview simulation session."""

    profile: dict[str, Any] = Field(..., description="Canonical profile used to build the deterministic InterviewPlan.")
    target_role: str | None = Field(default=None, description="Optional target role used to steer plan generation.")
    target_context_id: str | None = Field(default=None, description="Optional target context identifier.")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional session metadata carried as-is.")


class SubmitAnswerRequest(BaseModel):
    """Request payload for submitting an answer to the active question."""

    question_id: str = Field(description="ID of the active question being answered.")
    text: str = Field(description="Free-form answer text.")
    evidence_references: list[EvidenceReferenceRequest] = Field(default_factory=list, description="ADR-002 evidence references grounding the answer.")


class InterviewSessionResponse(BaseModel):
    """Transport DTO for an interview session."""

    session_id: str
    profile_id: str
    state: str
    current_question_index: int
    question_count: int
    answered_count: int
    current_question: dict[str, Any] | None = None
    answers: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubmitAnswerResponse(BaseModel):
    """Response payload for a submitted answer."""

    session: InterviewSessionResponse
    evaluation: dict[str, Any]


class AdvanceSessionResponse(BaseModel):
    """Response payload for advancing to the next question."""

    completed: bool
    session: InterviewSessionResponse
    next_question: dict[str, Any] | None = None
    report: dict[str, Any] | None = None


class InterviewReportResponse(BaseModel):
    """Response payload for a completed session report."""

    session_id: str
    summary: dict[str, Any]


@app.post("/profiles/{profile_id}/resolve")
def resolve_profile_recommendation(profile_id: str, request: ResolveRecommendationRequest) -> dict[str, Any]:
    """Apply a guided recommendation resolution to the canonical profile and persist it.

    Only the M1.7/M1.8 rule types are supported. The edit is deterministic and
    schema-compliant, the canonical YAML is rewritten, and the updated profile
    DTO is returned so the frontend can re-analyze.
    """
    if request.triggeredRule not in RESOLVABLE_RULES:
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="UNSUPPORTED_RULE",
            detail=f"Resolution is not supported for rule: {request.triggeredRule}",
        ).model_dump())

    try:
        record = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    try:
        apply_resolution(
            data,
            triggered_rule=request.triggeredRule,
            element_id=request.elementId,
            skill_ids=request.skillIds,
            experience_ids=request.experienceIds,
            technologies=request.technologies,
            achievement_statement=request.achievementStatement or "",
            summary_text=request.summaryText or "",
        )
    except (UnsupportedRuleError, InvalidAchievementError, AchievementNotMeasurableError, EmptySummaryError) as exc:
        error = {
            UnsupportedRuleError: "UNSUPPORTED_RULE",
            InvalidAchievementError: "INVALID_ACHIEVEMENT",
            AchievementNotMeasurableError: "ACHIEVEMENT_NOT_MEASURABLE",
            EmptySummaryError: "EMPTY_SUMMARY",
        }[type(exc)]
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error=error,
            detail=str(exc),
        ).model_dump())
    except ResolutionTargetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to apply resolution: {exc}",
        ).model_dump())

    try:
        Path(record.path).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to persist profile: {exc}",
        ).model_dump())

    try:
        updated = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    return {"profile": to_profile_details(updated.data, profile_id, state=updated.state)}


@app.post("/profiles/{profile_id}/artifacts/{artifact_id}/regenerate")
def regenerate_profile_artifact(
    profile_id: str,
    artifact_id: str,
    request: RegenerateArtifactRequest,
) -> dict[str, Any]:
    """Explicitly regenerate a stale artifact from the canonical profile.

    Rebuilds the ExportContract and regenerates Markdown/DOCX through the existing
    generation pipeline, then clears the artifact's stale flag and persists the
    updated profile. The generated output is returned to the client; previously
    generated content is never mutated in place.
    """
    try:
        record = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    artifact = next(
        (a for a in data.get("artifacts", []) if a.get("id") == artifact_id),
        None,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=f"Artifact not found: {artifact_id}",
        ).model_dump())

    try:
        result = generate_artifact(
            record.path,
            artifact_id,
            request.output_format,
            SCHEMA_LOADER,
            job_description=request.job_description,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="VALIDATION_ERROR",
            detail=str(exc),
        ).model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to regenerate artifact: {exc}",
        ).model_dump())

    if request.job_description and isinstance(result, tuple):
        output, optimization_result = result
    else:
        output = result
        optimization_result = None

    artifact["status"] = _ARTIFACT_STATUS_CURRENT
    artifact["derivedFromProfileVersion"] = data.get("profileVersion", "")

    try:
        Path(record.path).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to persist profile: {exc}",
        ).model_dump())

    response: dict[str, Any] = {
        "artifactId": artifact_id,
        "output_format": request.output_format,
        "artifact": output.decode("utf-8") if isinstance(output, bytes) else output,
        "status": _ARTIFACT_STATUS_CURRENT,
        "profile": to_profile_details(data, profile_id, state=record.state),
    }

    if optimization_result is not None:
        response["optimizationStatus"] = optimization_result.status.value
        response["optimizationMessage"] = optimization_result.message
        if optimization_result.summary:
            response["optimizationSummary"] = optimization_result.summary.to_dict()
        if optimization_result.recommendations:
            response["recommendations"] = [
                rec.to_dict() for rec in optimization_result.recommendations
            ]

    return response


@app.get("/technologies")
def list_technology_keywords() -> dict[str, Any]:
    """List the technology keywords recognized by the recommendation engine."""
    return {"keywords": sorted(set(TECHNOLOGY_KEYWORDS))}





@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return the health status of the API."""
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    """Return the API version."""
    return VersionResponse(version=BACKEND_VERSION)


@app.get("/artifact-templates")
def list_artifact_templates() -> list[dict[str, str]]:
    """Return all available artifact templates."""
    return default_template_registry().list()


@app.post("/artifact-templates/{template_id}/preview")
def preview_artifact_template(template_id: str, request: TemplatePreviewRequest) -> dict[str, Any]:
    """Render a template preview for a profile (render-only, no side effects).

    Transport-only wrapper around the existing generation pipeline: the template
    renders markdown from the current canonical profile without creating an
    artifact, persisting anything, or re-running the reasoning engine.
    """
    try:
        record = PROFILE_REPOSITORY.get(request.profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    registry = default_template_registry()
    try:
        template = registry.get(template_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="INVALID_TEMPLATE",
            detail=f"Unknown artifact template: '{template_id}'. Available: {[t['id'] for t in registry.list()]}",
        ).model_dump())

    try:
        markdown = template.preview(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="VALIDATION_ERROR",
            detail=str(exc),
        ).model_dump())
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to render template preview: {exc}",
        ).model_dump())

    virtual_artifact = template.build(data, title="Preview")
    try:
        health_score = run_profile_quality(data).health_score
    except Exception:
        health_score = None

    return {
        "markdown": markdown,
        "source_count": len(virtual_artifact.get("sourceRefs", [])),
        "estimated_health_score": health_score,
    }


ACCEPTED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/profiles", response_model=list[ProfileInfo])
def list_profiles() -> list[ProfileInfo]:
    """Return metadata for all available profiles."""
    profiles: list[ProfileInfo] = []
    if not PROFILES_ROOT.exists():
        return profiles

    for record in PROFILE_REPOSITORY.list():
        if not isinstance(record.data, dict):
            continue

        summary = to_profile_summary(record.data, record.profile_id, state=record.state)

        profiles.append(ProfileInfo(
            id=summary["id"],
            name=summary["name"],
            artifactCount=summary["artifactCount"],
            artifactIds=summary["artifactIds"],
            headline=summary["headline"],
            importedAt=summary["importedAt"],
            state=summary["state"],
        ))

    return profiles


def _to_classification_info(
    classification: ImportClassification,
) -> ImportClassificationInfo:
    """Map a core import classification to its transport DTO."""
    return ImportClassificationInfo(
        result=classification.result,
        candidates=[
            ImportCandidate(
                profileId=candidate.profile_id,
                matchedOn=list(candidate.matched_on),
                conflictingOn=list(candidate.conflicting_on),
            )
            for candidate in classification.candidates
        ],
    )


def _colliding_record(exc: DuplicateProfileError) -> ProfileRecord | None:
    """Best-effort lookup of the profile record that blocked an import."""
    try:
        return PROFILE_REPOSITORY.get(Path(exc.existing_path).stem)
    except (EntityNotFoundError, ValueError):
        return None


def _same_source_document(record: ProfileRecord | None, source_hash: str) -> bool:
    """True when a colliding record was produced from the same source bytes."""
    if record is None:
        return False
    data = record.data if isinstance(record.data, dict) else {}
    extensions = data.get("extensions") or {}
    if not isinstance(extensions, dict):
        extensions = {}
    acquisition = extensions.get("_acquisition") or {}
    if not isinstance(acquisition, dict):
        acquisition = {}
    return (
        str(acquisition.get("sourceHash") or "").strip().lower()
        == (source_hash or "").strip().lower()
    )


@app.post("/profiles/import", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
def import_profile(file: UploadFile = File(...)) -> ImportResponse:
    """Import a CV document, run the acquisition pipeline, and create a canonical profile."""
    if not file.filename:
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="INVALID_FILE",
            detail="No file provided.",
        ).model_dump())

    suffix = Path(file.filename).suffix.lower()
    mime_type_to_check = file.content_type or ""

    if mime_type_to_check not in ACCEPTED_MIME_TYPES and suffix not in {".docx", ".doc", ".txt"}:
        accepted_list = ", ".join(sorted(ACCEPTED_MIME_TYPES))
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="INVALID_FILE",
            detail=f"Unsupported file type: {mime_type_to_check or suffix}. Accepted types: {accepted_list}",
        ).model_dump())

    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="FILE_TOO_LARGE",
            detail=f"File size {len(contents) / 1024 / 1024:.1f} MB exceeds maximum of {MAX_UPLOAD_SIZE / 1024 / 1024:.0f} MB",
        ).model_dump())

    source_name = file.filename or "uploaded_cv.docx"
    source_hash = source_hash_for_bytes(contents)

    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / (file.filename or "uploaded_cv.docx")
    try:
        temp_path.write_bytes(contents)
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to save uploaded file: {exc}",
        ).model_dump())
    finally:
        file.file.close()

    try:
        pipeline = AcquisitionPipeline()
        profile_path = pipeline.run(
            str(temp_path),
            source_metadata={
                "sourceName": source_name,
                "sourceHash": source_hash,
            },
        )
    except DuplicateProfileError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Phase 2B: an import that collides with an existing person.id is
        # idempotent when the colliding record was produced from the exact
        # same source document; otherwise the duplicate is real and 409.
        existing = _colliding_record(exc)
        if _same_source_document(existing, source_hash):
            classification = ImportClassification(
                result=SAME_DOCUMENT,
                candidates=(
                    CandidateMatch(
                        profile_id=existing.profile_id,
                        matched_on=("sourceHash",),
                    ),
                ),
            )
            return ImportResponse(
                profileId=existing.profile_id,
                profile=ProfileInfo(
                    **to_profile_summary(
                        existing.data,
                        existing.profile_id,
                        state=existing.state,
                    )
                ),
                classification=_to_classification_info(classification),
            )
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="DUPLICATE_PROFILE",
            detail=str(exc),
        ).model_dump())
    except (DocumentReadError, PipelineError, LLMExtractionError) as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="IMPORT_FAILED",
            detail="Could not extract a valid profile from the document.",
            processingErrors=[str(exc)],
        ).model_dump())
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Profile import failed: {exc}",
        ).model_dump())

    # Phase 2A: retain the original uploaded document (byte-identical) in the
    # gitignored staging source store before the temporary copy is removed.
    try:
        sources_dir = PROFILES_ROOT / "staging" / "_sources"
        retain_source(contents, sources_dir, source_hash, suffix)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Failed to retain source document in %s: %s", sources_dir, exc
        )

    shutil.rmtree(temp_dir, ignore_errors=True)

    profile_id = Path(profile_path).stem
    try:
        with open(profile_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to read imported profile: {exc}",
        ).model_dump())

    classification = classify_import(
        PROFILE_REPOSITORY.list(),
        source_hash=source_hash,
        profile_data=data,
        exclude_profile_id=profile_id,
    )

    return ImportResponse(
        profileId=profile_id,
        profile=ProfileInfo(**to_profile_summary(data, profile_id, state=ProfileState.STAGING)),
        classification=_to_classification_info(classification),
    )


@app.get("/profiles/{profile_id}", response_model=dict[str, Any])
def get_profile(profile_id: str) -> dict[str, Any]:
    """Return the full profile detail DTO for a given profile."""
    try:
        record = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    return to_profile_details(data, profile_id, state=record.state)


@app.get("/profiles/{profile_id}/canonical", response_model=dict[str, Any])
def get_canonical_profile(profile_id: str) -> dict[str, Any]:
    """Return the validated canonical profile exactly as persisted.

    Transport-only: no flattening or transformation. The canonical profile is
    the single source of career data and is consumed by Interview Simulation,
    artifact generation, and future modules — never the presentation DTO.
    """
    try:
        record = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    return data


@app.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str) -> None:
    """Delete a profile and its associated data from the filesystem."""
    try:
        PROFILE_REPOSITORY.delete(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())
    except OSError as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to delete profile: {exc}",
        ).model_dump())


@app.post("/profiles/{profile_id}/artifacts", response_model=CreateArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_profile_artifact(profile_id: str, request: CreateArtifactRequest) -> CreateArtifactResponse:
    """Create an artifact definition from a template and persist it to the profile."""
    try:
        record = PROFILE_REPOSITORY.get(profile_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    registry = default_template_registry()
    try:
        template = registry.get(request.template)
    except KeyError:
        raise HTTPException(status_code=400, detail=ApiErrorResponse(
            error="INVALID_TEMPLATE",
            detail=f"Unknown artifact template: '{request.template}'. Available: {[t['id'] for t in registry.list()]}",
        ).model_dump())

    artifact = template.build(data, title=request.title)
    artifacts: list[dict[str, Any]] = data.get("artifacts", [])
    artifacts.append(artifact)
    data["artifacts"] = artifacts

    try:
        Path(record.path).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail=f"Failed to persist artifact: {exc}",
        ).model_dump())

    return CreateArtifactResponse(artifactId=artifact["id"], artifact=artifact)


@app.post("/analyze", response_model=dict[str, Any])
def analyze_profile(request: AnalyzeRequest) -> dict[str, Any]:
    """Run deterministic analysis of a canonical profile using the Reasoning Engine.

    Returns a ReasoningReport with findings, findings organized by type,
    a summary, and execution statistics — all without generating any artifacts.
    """
    try:
        record = PROFILE_REPOSITORY.get(request.profileId)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=str(exc),
        ).model_dump())

    data = record.data

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="INTERNAL_ERROR",
            detail="Profile data is malformed.",
        ).model_dump())

    from careeros.reasoning import ReasoningEngine, create_default_registry

    try:
        registry = create_default_registry()
        engine = ReasoningEngine(registry)
        report = engine.analyze(data, parameters=request.parameters)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=ApiErrorResponse(
            error="ANALYSIS_ERROR",
            detail=str(exc),
        ).model_dump())

    return report.to_dict()


@app.get("/schemas", response_model=list[str])
def list_schemas() -> list[str]:
    """Return the names of all available schemas."""
    return SCHEMA_LOADER.discover_entity_names()


@app.get("/schemas/{entity}", response_model=SchemaInfoResponse)
def get_schema(entity: str) -> SchemaInfoResponse:
    """Return metadata for a given schema."""
    try:
        schema = SCHEMA_LOADER.load_schema(entity)
    except SchemaLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SchemaInfoResponse(
        title=schema.get("title", entity),
        description=schema.get("description", "No description available."),
        version=schema.get("version", "unknown"),
    )


@app.post("/validate/{entity}", response_model=dict[str, Any])
def validate_entity(entity: str, request: ValidationRequest) -> dict[str, Any]:
    """Validate a payload against the schema for an entity."""
    try:
        result = VALIDATOR.validate_entity(request.payload, entity)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SchemaLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"entity": entity, "valid": result.is_valid, "errors": result.errors}


@app.post("/create/{entity}", response_model=EntityResponse)
def create_entity(entity: str, request: ValidationRequest) -> EntityResponse:
    """Create a new entity using the repository layer."""
    try:
        record = REPOSITORY.save(entity, request.payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EntityResponse(entity_type=record.entity_type, id=record.id, data=record.data)


@app.post("/search/{entity}", response_model=list[EntityResponse])
def search_entities(entity: str, request: SearchRequest) -> list[EntityResponse]:
    """Search persisted entities by a field value."""
    matches: list[EntityResponse] = []
    entity_dir = REPO_ROOT / "data" / entity
    if not entity_dir.exists():
        return []

    for path in sorted(entity_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get(request.field) == request.value:
            matches.append(EntityResponse(entity_type=entity, id=str(payload.get("id", path.stem)), data=payload))

    return matches


@app.post("/generate/markdown-cv", response_class=PlainTextResponse)
def generate_markdown_cv_endpoint(request: MarkdownCVRequest) -> PlainTextResponse:
    """Generate a Markdown CV from a profile file and artifact id."""
    try:
        if request.profile_path:
            profile_path = request.profile_path
        else:
            profile_path = PROFILE_REPOSITORY.get(request.profile_id).path
        markdown = generate_markdown_cv(profile_path, request.artifact_id, SCHEMA_LOADER)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PlainTextResponse(markdown, media_type="text/markdown")


@app.post("/generate/artifact")
def generate_artifact_endpoint(request: GenerateArtifactRequest) -> Response:
    """Generate an artifact through the generator registry.
    
    When job_description is provided, generates a tailored artifact with recommendations applied.
    Returns optimization status and recommendations in custom headers when tailoring.
    """
    try:
        if request.profile_path:
            profile_path = request.profile_path
        else:
            profile_path = PROFILE_REPOSITORY.get(request.profile_id).path
        result = generate_artifact(
            profile_path, 
            request.artifact_id, 
            request.output_format, 
            SCHEMA_LOADER,
            job_description=request.job_description
        )
        
        if request.job_description and isinstance(result, tuple):
            output, optimization_result = result
        else:
            output = result
            optimization_result = None
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    media_type = _media_type_for_format(request.output_format)
    headers = {}
    
    if optimization_result is not None:
        headers["X-Optimization-Status"] = optimization_result.status.value
        headers["X-Optimization-Message"] = optimization_result.message
        if optimization_result.summary:
            headers["X-Optimization-Summary"] = json.dumps(optimization_result.summary.to_dict())
        if optimization_result.recommendations:
            headers["X-Recommendations"] = json.dumps([rec.to_dict() for rec in optimization_result.recommendations])
    
    if isinstance(output, bytes):
        return Response(content=output, media_type=media_type, headers=headers)
    return Response(content=output, media_type=media_type, headers=headers)


@app.post("/optimize-cv", response_model=dict[str, Any])
def optimize_cv_endpoint(request: OptimizeCVRequest) -> dict[str, Any]:
    """Generate structured optimization recommendations for a CV artifact."""
    try:
        optimizer = CVOptimizer(request.profile)
        result = optimizer.optimize_cv(request.artifact_id, request.job_description)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result.to_dict()


@app.get("/entities/{entity}", response_model=list[EntityResponse])
def list_entities(entity: str) -> list[EntityResponse]:
    """List all persisted entities of a given type."""
    entity_dir = REPO_ROOT / "data" / entity
    if not entity_dir.exists():
        return []

    records: list[EntityResponse] = []
    for path in sorted(entity_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        records.append(EntityResponse(entity_type=entity, id=str(payload.get("id", path.stem)), data=payload))
    return records


@app.get("/entities/{entity}/{id}", response_model=EntityResponse)
def get_entity(entity: str, id: str) -> EntityResponse:
    """Retrieve a persisted entity by identifier."""
    try:
        record = REPOSITORY.get(entity, id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EntityResponse(entity_type=record.entity_type, id=record.id, data=record.data)


@app.post("/entities/{entity}", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity_record(entity: str, payload: dict[str, Any]) -> EntityResponse:
    """Create a new entity payload via the repository."""
    try:
        record = REPOSITORY.save(entity, payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EntityResponse(entity_type=record.entity_type, id=record.id, data=record.data)


@app.put("/entities/{entity}/{id}", response_model=EntityResponse)
def update_entity(entity: str, id: str, payload: dict[str, Any]) -> EntityResponse:
    """Update an existing entity via the repository."""
    try:
        record = REPOSITORY.update(entity, id, payload)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EntityResponse(entity_type=record.entity_type, id=record.id, data=record.data)


@app.delete("/entities/{entity}/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity: str, id: str) -> None:
    """Delete an entity via the repository."""
    try:
        REPOSITORY.delete(entity, id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Interview Simulation API (M1.19)
# ---------------------------------------------------------------------------

_INTERVIEW_SESSIONS: dict[str, InterviewSession] = {}
SESSION_ENGINE = SessionEngine()
EVALUATION_ENGINE = EvaluationEngine()
INTERVIEW_ENGINE = InterviewEngine()


def _get_interview_session(session_id: str) -> InterviewSession:
    """Resolve a live session from the in-memory registry (M1.19: no persistence)."""
    session = _INTERVIEW_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=f"Interview session not found: {session_id}",
        ).model_dump())
    return session


def _store_interview_session(session: InterviewSession) -> None:
    """Keep an updated session in the in-memory registry."""
    _INTERVIEW_SESSIONS[session.session_id] = session


@app.post("/interviews/sessions", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
def create_interview_session(request: CreateInterviewSessionRequest) -> InterviewSessionResponse:
    """Create and start an interview simulation session from a canonical profile.

    Builds a deterministic ``InterviewPlan`` via ``InterviewEngine`` and starts a
    session via ``SessionEngine``. The API performs no evaluation or report
    assembly itself (M1.19 spec).
    """
    try:
        plan = INTERVIEW_ENGINE.generate_plan(
            request.profile,
            target_role=request.target_role,
            target_context_id=request.target_context_id,
        )
    except InvalidProfileError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="INVALID_PROFILE",
            detail=str(exc),
        ).model_dump())

    session = SESSION_ENGINE.create_session(
        plan=plan,
        session_id=uuid4().hex,
        metadata=request.metadata,
    )
    session = SESSION_ENGINE.start_session(session)
    _store_interview_session(session)
    return InterviewSessionResponse(**to_session_response(session))


@app.post("/interviews/sessions/{session_id}/answers", response_model=SubmitAnswerResponse)
def submit_interview_answer(session_id: str, request: SubmitAnswerRequest) -> SubmitAnswerResponse:
    """Record an answer for the active question and return evaluation signals.

    Evaluation is delegated to the domain ``EvaluationEngine``; the API only
    orchestrates and maps the results into the response DTO.
    """
    session = _get_interview_session(session_id)
    current = session.current_question_instance()
    if current is None:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="NO_ACTIVE_QUESTION",
            detail="No active question to answer.",
        ).model_dump())

    answer = InterviewAnswer(
        question_id=request.question_id,
        text=request.text,
        evidence_references=tuple(
            {"id": ref.id, "type": ref.type} for ref in request.evidence_references
        ),
    )

    try:
        evaluation = EVALUATION_ENGINE.evaluate_answer(current.question, answer)
    except InvalidQuestionError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_QUESTION",
            detail=str(exc),
        ).model_dump())
    except MissingEvidenceReferenceError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="MISSING_EVIDENCE_REFERENCE",
            detail=str(exc),
        ).model_dump())
    except InvalidAnswerError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="INVALID_ANSWER",
            detail=str(exc),
        ).model_dump())

    try:
        updated = SESSION_ENGINE.submit_answer(session, answer)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_SESSION_STATE",
            detail=str(exc),
        ).model_dump())
    except InvalidQuestionError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_QUESTION",
            detail=str(exc),
        ).model_dump())
    except InvalidAnswerError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="INVALID_ANSWER",
            detail=str(exc),
        ).model_dump())
    except NoActiveQuestionError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="NO_ACTIVE_QUESTION",
            detail=str(exc),
        ).model_dump())

    _store_interview_session(updated)
    return SubmitAnswerResponse(
        session=InterviewSessionResponse(**to_session_response(updated)),
        evaluation=evaluation.to_dict(),
    )


@app.post("/interviews/sessions/{session_id}/next", response_model=AdvanceSessionResponse)
def advance_interview_session(session_id: str) -> AdvanceSessionResponse:
    """Advance the session to the next question or complete it deterministically."""
    session = _get_interview_session(session_id)
    try:
        advanced = SESSION_ENGINE.next_question(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_SESSION_STATE",
            detail=str(exc),
        ).model_dump())
    except NoActiveQuestionError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="NO_ACTIVE_QUESTION",
            detail=str(exc),
        ).model_dump())

    _store_interview_session(advanced)
    completed = advanced.state == InterviewSessionState.COMPLETED
    next_question = advanced.current_question_instance()
    report = None
    if completed:
        report = SESSION_ENGINE.build_report(advanced).to_dict()
    return AdvanceSessionResponse(
        completed=completed,
        session=InterviewSessionResponse(**to_session_response(advanced)),
        next_question=next_question.to_dict() if next_question else None,
        report=report,
    )


@app.post("/interviews/sessions/{session_id}/pause", response_model=InterviewSessionResponse)
def pause_interview_session(session_id: str) -> InterviewSessionResponse:
    """Pause an in-progress session, preserving runtime state."""
    session = _get_interview_session(session_id)
    try:
        paused = SESSION_ENGINE.pause_session(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_SESSION_STATE",
            detail=str(exc),
        ).model_dump())
    _store_interview_session(paused)
    return InterviewSessionResponse(**to_session_response(paused))


@app.post("/interviews/sessions/{session_id}/resume", response_model=InterviewSessionResponse)
def resume_interview_session(session_id: str) -> InterviewSessionResponse:
    """Resume a paused session, restoring the active question context."""
    session = _get_interview_session(session_id)
    try:
        resumed = SESSION_ENGINE.resume_session(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_SESSION_STATE",
            detail=str(exc),
        ).model_dump())
    _store_interview_session(resumed)
    return InterviewSessionResponse(**to_session_response(resumed))


@app.get("/interviews/sessions/{session_id}", response_model=InterviewSessionResponse)
def get_interview_session(session_id: str) -> InterviewSessionResponse:
    """Retrieve the current interview session state."""
    return InterviewSessionResponse(**to_session_response(_get_interview_session(session_id)))


@app.get("/interviews/sessions/{session_id}/report", response_model=InterviewReportResponse)
def get_interview_report(session_id: str) -> InterviewReportResponse:
    """Return the deterministic summary report for a completed session."""
    session = _get_interview_session(session_id)
    if session.state not in (InterviewSessionState.COMPLETED, InterviewSessionState.REVIEWED):
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="SESSION_NOT_COMPLETED",
            detail="The interview report is only available for completed sessions.",
        ).model_dump())
    try:
        report = SESSION_ENGINE.build_report(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_SESSION_STATE",
            detail=str(exc),
        ).model_dump())
    return InterviewReportResponse(session_id=report.session_id, summary=report.summary.to_dict())


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return consistent error responses for malformed requests."""
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": exc.errors()})


@app.exception_handler(CareerOSException)
def handle_careeros_exception(request: Request, exc: CareerOSException) -> JSONResponse:
    """Return consistent error responses for core library exceptions."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(InterviewSimulationError)
def handle_interview_simulation_error(request: Request, exc: InterviewSimulationError) -> JSONResponse:
    """Translate unhandled Interview Simulation domain errors consistently."""
    return JSONResponse(status_code=500, content=ApiErrorResponse(
        error="INTERNAL_ERROR",
        detail=str(exc),
    ).model_dump())


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Return consistent JSON error responses."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _media_type_for_format(output_format: str) -> str:
    """Resolve the response media type for an output format."""
    normalized_format = output_format.strip().lower()
    if normalized_format == "markdown":
        return "text/markdown"
    if normalized_format == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"
