"""FastAPI application for CareerOS."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import yaml

from careeros import CVOptimizer, EntityValidator, FileSystemRepository, OptimizationResult, OptimizationStatus, ProfileLoader, SchemaLoader, generate_artifact, generate_markdown_cv
from careeros.exceptions import CareerOSException, EntityNotFoundError, RepositoryError, SchemaLoadError, ValidationError

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

app = FastAPI(title="CareerOS API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schemas"
PROFILES_ROOT = REPO_ROOT / "profiles"
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


def resolve_profile_path(profile_id: str) -> Path:
    """Resolve a profile_id to its filesystem path under the profiles directory."""
    profile_path = PROFILES_ROOT / f"{profile_id}.yaml"
    if not profile_path.exists():
        profile_path = PROFILES_ROOT / f"{profile_id}.yml"
    if not profile_path.exists():
        profile_path = PROFILES_ROOT / f"{profile_id}.json"
    if not profile_path.exists():
        raise EntityNotFoundError(f"Profile not found: {profile_id}")
    return profile_path


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return the health status of the API."""
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    """Return the API version."""
    return VersionResponse(version="1.0.0")


@app.get("/profiles", response_model=list[ProfileInfo])
def list_profiles() -> list[ProfileInfo]:
    """Return metadata for all available profiles."""
    profiles: list[ProfileInfo] = []
    if not PROFILES_ROOT.exists():
        return profiles

    for path in sorted(PROFILES_ROOT.glob("*")):
        if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
            continue
        profile_id = path.stem
        try:
            with path.open("r", encoding="utf-8") as handle:
                if path.suffix == ".json":
                    import json as _json
                    data = _json.load(handle)
                else:
                    data = yaml.safe_load(handle)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        person = data.get("person", {})
        names = person.get("names", [])
        name = names[0].get("value", profile_id) if names else profile_id
        artifacts = data.get("artifacts", [])
        artifact_ids = [a.get("id") for a in artifacts if a.get("id")]

        profiles.append(ProfileInfo(
            id=profile_id,
            name=name,
            artifactCount=len(artifacts),
            artifactIds=artifact_ids,
        ))

    return profiles


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
        profile_path = request.profile_path or resolve_profile_path(request.profile_id)
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
        profile_path = request.profile_path or resolve_profile_path(request.profile_id)
        output = generate_artifact(
            profile_path, 
            request.artifact_id, 
            request.output_format, 
            SCHEMA_LOADER,
            job_description=request.job_description
        )
        
        optimization_result = None
        if request.job_description:
            profile = ProfileLoader(SCHEMA_LOADER).load(profile_path)
            optimizer = CVOptimizer(profile)
            optimization_result = optimizer.optimize_cv(request.artifact_id, request.job_description)
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
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _media_type_for_format(output_format: str) -> str:
    """Resolve the response media type for an output format."""
    normalized_format = output_format.strip().lower()
    if normalized_format == "markdown":
        return "text/markdown"
    if normalized_format == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"
