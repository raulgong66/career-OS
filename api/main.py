"""FastAPI application for CareerOS."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

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

try:
    runtime_config = validate_runtime_config()
except RuntimeConfigurationError as exc:
    print(f"CareerOS startup aborted: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
print_configuration_banner(runtime_config)

from careeros import CVOptimizer, EntityValidator, FileSystemRepository, OptimizationResult, OptimizationStatus, ProfileLoader, SchemaLoader, TemplateRegistry, default_template_registry, generate_artifact, generate_markdown_cv
from careeros.exceptions import CareerOSException, EntityNotFoundError, RepositoryError, SchemaLoadError, ValidationError
from careeros.acquisition import AcquisitionPipeline, DocumentReadError, PipelineError
from careeros.profile_repository import ProfileRepository, ProfileState
from careeros.interview import (
    EvaluationEngine,
    EvaluationSummary,
    InterviewAnswer,
    InterviewEngine,
    InterviewReport,
    InterviewSession,
    InterviewSummary,
    SessionEngine,
    SessionMetrics,
    SessionState,
)
from careeros.interview.exceptions import InvalidProfileError
from careeros.interview.simulation.exceptions import (
    EvaluationPreconditionError,
    InvalidAnswerError,
    InvalidClaimError,
    InvalidQuestionError,
    InvalidSessionStateError,
    MissingEvidenceReferenceError,
    NoActiveQuestionError,
)

from .dto import to_import_response, to_profile_details, to_profile_summary
from careeros.reasoning.rules.recommendation_rules import TECHNOLOGY_KEYWORDS
from careeros.resolution import (
    AchievementNotMeasurableError,
    InvalidAchievementError,
    RESOLVABLE_RULES,
    ResolutionTargetNotFoundError,
    UnsupportedRuleError,
    _ARTIFACT_STATUS_CURRENT,
    apply_resolution,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

app = FastAPI(title="CareerOS API", version=BACKEND_VERSION)
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

# Interview simulation (M1.18). Session state is external runtime state, not
# profile state: it lives in an in-memory registry owned by the API layer.
# The engines are stateless and deterministic; persistence is deferred to the
# session-persistence milestone.
INTERVIEW_ENGINE = InterviewEngine()
SESSION_ENGINE = SessionEngine()
EVALUATION_ENGINE = EvaluationEngine()
_INTERVIEW_SESSIONS: dict[str, InterviewSession] = {}


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


class ImportResponse(BaseModel):
    """Response after a successful profile import."""

    profileId: str = Field(description="Identifier of the imported profile.")
    profile: ProfileInfo = Field(description="Profile summary DTO.")


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


class RegenerateArtifactRequest(BaseModel):
    """Request payload for explicitly regenerating a stale artifact.

    Regeneration always rebuilds the ExportContract from the canonical profile
    through the existing generation pipeline. It never mutates previously
    generated markdown/docx directly.
    """

    output_format: str = Field(default="markdown", description="Output format to regenerate (markdown or docx).")
    job_description: Optional[str] = Field(default=None, description="Optional job description to reproduce a tailored artifact.")


class CreateInterviewSessionRequest(BaseModel):
    """Request payload for creating an interview simulation session."""

    profile_id: str = Field(description="Profile identifier (filename without extension).")
    target_role: Optional[str] = Field(default=None, description="Optional target role to tailor the question plan.")


class SubmitInterviewAnswerRequest(BaseModel):
    """Request payload for submitting an answer to the current question."""

    text: str = Field(description="The candidate's answer text.")
    duration_seconds: Optional[int] = Field(default=None, description="Optional time spent answering in seconds.")


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
        )
    except (UnsupportedRuleError, InvalidAchievementError, AchievementNotMeasurableError) as exc:
        error = {
            UnsupportedRuleError: "UNSUPPORTED_RULE",
            InvalidAchievementError: "INVALID_ACHIEVEMENT",
            AchievementNotMeasurableError: "ACHIEVEMENT_NOT_MEASURABLE",
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


# ---------------------------------------------------------------------------
# Interview simulation (M1.18)
# ---------------------------------------------------------------------------


def _get_interview_session(session_id: str) -> InterviewSession:
    """Resolve a live session from the in-memory registry."""
    session = _INTERVIEW_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=ApiErrorResponse(
            error="NOT_FOUND",
            detail=f"Interview session not found: {session_id}",
        ).model_dump())
    return session


def _store_interview_session(session: InterviewSession) -> None:
    """Persist an updated session into the in-memory registry."""
    _INTERVIEW_SESSIONS[session.id] = session


def _attach_summary(session: InterviewSession, summary: InterviewSummary) -> InterviewSession:
    """Attach a computed ``InterviewSummary`` to a completed session."""
    return InterviewSession(
        id=session.id,
        plan_ref=session.plan_ref,
        profile_id=session.profile_id,
        state=session.state,
        questions=session.questions,
        answers=session.answers,
        started_at=session.started_at,
        completed_at=session.completed_at,
        paused_at=session.paused_at,
        metrics=session.metrics,
        summary=summary,
        metadata=session.metadata,
    )


def _build_report(
    session: InterviewSession,
    evaluation_summary: EvaluationSummary,
) -> InterviewReport:
    """Build the export-oriented report for a completed session.

    Strengths / weaknesses / recommendations are advisory text derived
    deterministically from the qualitative evaluation counts (ADR-003) —
    never numeric scores and never fabricated assertions.
    """
    total = evaluation_summary.total_answers or 1
    dimensions = (
        ("Coverage", evaluation_summary.coverage, "answers addressed the question intent"),
        ("Evidence", evaluation_summary.evidence, "answers were grounded in canonical profile evidence"),
        ("Claim alignment", evaluation_summary.claim_alignment, "answers aligned with the question competencies"),
        ("Measurability", evaluation_summary.measurability, "answers included a measurable outcome"),
        ("Structure", evaluation_summary.structure, "answers followed a structured (STAR) narrative"),
    )
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    for name, count, qualifier in dimensions:
        if count > 0:
            strengths.append(f"{name}: {count} of {total} {qualifier}.")
        if count < total:
            weaknesses.append(f"{name}: only {count} of {total} {qualifier}.")
    if evaluation_summary.inconsistent_answers:
        weaknesses.append(
            f"Consistency: {evaluation_summary.inconsistent_answers} answer(s) "
            "contained contradictory or unsupported claims."
        )
    if weaknesses:
        recommendations.append(
            "Ground answers in canonical profile evidence and keep claims consistent."
        )
        if evaluation_summary.measurability < total:
            recommendations.append(
                "Include a measurable outcome (metric, percentage, or business result) in each answer."
            )
        if evaluation_summary.structure < total:
            recommendations.append(
                "Structure answers around Situation, Task, Action, and Result (STAR)."
            )

    return InterviewReport(
        id=f"{session.id}:report",
        session_id=session.id,
        profile_id=session.profile_id,
        plan_ref=session.plan_ref,
        summary=session.summary or SESSION_ENGINE.build_summary(session),
        session_metrics=session.metrics or SessionMetrics(),
        answers=session.answers,
        strengths=tuple(strengths),
        weaknesses=tuple(weaknesses),
        recommendations=tuple(recommendations),
    )


@app.post("/interviews/sessions", status_code=status.HTTP_201_CREATED)
def create_interview_session(request: CreateInterviewSessionRequest) -> dict[str, Any]:
    """Create and start an interview simulation session for a profile.

    Builds a deterministic ``InterviewPlan`` from the canonical profile with
    ``InterviewEngine`` and starts a session via ``SessionEngine``. The
    returned session carries the materialized question instances; the first
    question is served by ``POST /interviews/sessions/{id}/next``.
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

    try:
        plan = INTERVIEW_ENGINE.generate_plan(data, target_role=request.target_role)
    except InvalidProfileError as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="INVALID_PROFILE",
            detail=str(exc),
        ).model_dump())

    session = SESSION_ENGINE.create_session(
        plan,
        session_id=f"interview-{uuid.uuid4().hex[:12]}",
    )
    session = SESSION_ENGINE.start_session(session)
    _store_interview_session(session)
    return session.to_dict()


@app.post("/interviews/sessions/{session_id}/answers")
def submit_interview_answer(
    session_id: str,
    request: SubmitInterviewAnswerRequest,
) -> dict[str, Any]:
    """Record an answer to the active question with immediate evaluation.

    The answer is evaluated deterministically by ``EvaluationEngine`` and
    stored on the session with its ``AnswerEvaluation`` and ``InterviewFeedback``
    so the candidate sees results immediately after answering.
    """
    session = _get_interview_session(session_id)
    try:
        question = SESSION_ENGINE.next_question(session)
    except NoActiveQuestionError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="NO_ACTIVE_QUESTION",
            detail=str(exc),
        ).model_dump())

    answer = InterviewAnswer(
        id=f"{session.id}:{question.id}:answer",
        session_id=session.id,
        question_id=question.id,
        text=request.text,
        duration_seconds=request.duration_seconds,
    )
    try:
        evaluation = EVALUATION_ENGINE.evaluate_answer(answer, question, session)
        feedback = EVALUATION_ENGINE.build_feedback(answer, question, session, evaluation)
    except (
        InvalidAnswerError,
        InvalidQuestionError,
        MissingEvidenceReferenceError,
        InvalidClaimError,
        EvaluationPreconditionError,
    ) as exc:
        raise HTTPException(status_code=422, detail=ApiErrorResponse(
            error="INVALID_ANSWER",
            detail=str(exc),
        ).model_dump())

    evaluated = InterviewAnswer(
        id=answer.id,
        session_id=answer.session_id,
        question_id=answer.question_id,
        text=answer.text,
        answered_at=answer.answered_at,
        duration_seconds=answer.duration_seconds,
        evaluation=evaluation,
        feedback=feedback,
    )
    try:
        session = SESSION_ENGINE.submit_answer(session, evaluated)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_STATE",
            detail=str(exc),
        ).model_dump())
    _store_interview_session(session)
    return {"session": session.to_dict(), "answer": evaluated.to_dict()}


@app.post("/interviews/sessions/{session_id}/next")
def advance_interview_session(session_id: str) -> dict[str, Any]:
    """Advance the session to the next question or complete it.

    When the question sequence is exhausted the session is completed, an
    ``EvaluationSummary`` and ``InterviewSummary`` are computed, and the
    export-oriented ``InterviewReport`` is returned alongside the session.
    """
    session = _get_interview_session(session_id)
    try:
        question = SESSION_ENGINE.next_question(session)
    except NoActiveQuestionError:
        completed = SESSION_ENGINE.complete_session(session)
        evaluation_summary = EVALUATION_ENGINE.evaluate_session(completed)
        summary = SESSION_ENGINE.build_summary(completed)
        completed = _attach_summary(completed, summary)
        _store_interview_session(completed)
        report = _build_report(completed, evaluation_summary)
        return {
            "completed": True,
            "session": completed.to_dict(),
            "report": report.to_dict(),
        }
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_STATE",
            detail=str(exc),
        ).model_dump())
    return {"completed": False, "session": session.to_dict(), "question": question.to_dict()}


@app.post("/interviews/sessions/{session_id}/pause")
def pause_interview_session(session_id: str) -> dict[str, Any]:
    """Pause an in-progress interview session."""
    session = _get_interview_session(session_id)
    try:
        session = SESSION_ENGINE.pause_session(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_STATE",
            detail=str(exc),
        ).model_dump())
    _store_interview_session(session)
    return session.to_dict()


@app.post("/interviews/sessions/{session_id}/resume")
def resume_interview_session(session_id: str) -> dict[str, Any]:
    """Resume a paused interview session."""
    session = _get_interview_session(session_id)
    try:
        session = SESSION_ENGINE.resume_session(session)
    except InvalidSessionStateError as exc:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_STATE",
            detail=str(exc),
        ).model_dump())
    _store_interview_session(session)
    return session.to_dict()


@app.get("/interviews/sessions/{session_id}")
def get_interview_session(session_id: str) -> dict[str, Any]:
    """Retrieve the current state of an interview session."""
    return _get_interview_session(session_id).to_dict()


@app.get("/interviews/sessions/{session_id}/report")
def get_interview_report(session_id: str) -> dict[str, Any]:
    """Retrieve the export-oriented report for a completed session."""
    session = _get_interview_session(session_id)
    if session.state != SessionState.COMPLETED:
        raise HTTPException(status_code=409, detail=ApiErrorResponse(
            error="INVALID_STATE",
            detail="The interview report is only available for completed sessions.",
        ).model_dump())
    evaluation_summary = EVALUATION_ENGINE.evaluate_session(session)
    return _build_report(session, evaluation_summary).to_dict()





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
        profile_path = pipeline.run(str(temp_path))
    except (DocumentReadError, PipelineError) as exc:
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

    return ImportResponse(
        profileId=profile_id,
        profile=ProfileInfo(**to_profile_summary(data, profile_id, state=ProfileState.STAGING)),
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


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return consistent error responses for malformed requests."""
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": exc.errors()})


@app.exception_handler(CareerOSException)
def handle_careeros_exception(request: Request, exc: CareerOSException) -> JSONResponse:
    """Return consistent error responses for core library exceptions."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


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
