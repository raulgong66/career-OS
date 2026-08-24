"""Mission Builder API routes (Phase 2 MVP).

Mounted into the main FastAPI app from ``api/main.py``. The router is
transport-only (ADR-009): it loads the canonical profile, interprets the
mission through the provider-neutral interpreter, and returns deterministic
serialized outputs produced by ``careeros.mission``. No scoring, reasoning,
or business rules live here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from careeros.ai import create_ai_provider
from careeros.exceptions import EntityNotFoundError
from careeros.mission import (
    MissionContract,
    MissionContractError,
    MissionInterpretationError,
    MissionInterpreter,
    evaluate_mission,
    evaluate_mission_many,
)
from careeros.profile_repository import ProfileRepository


def _default_profiles_root() -> Path:
    """Resolve the canonical profiles directory relative to this package."""
    return Path(__file__).resolve().parents[2] / "profiles"


def _error(status_code: int, error: str, detail: str) -> HTTPException:
    """Build a consistent API error response (matches ``ApiErrorResponse``)."""
    return HTTPException(status_code=status_code, detail={"error": error, "detail": detail})


class InterpretMissionRequest(BaseModel):
    """Request payload for interpreting a mission into a Mission Contract."""

    mission: str = Field(..., min_length=1, description="The business mission in natural language.")


class EvaluateMissionRequest(BaseModel):
    """Request payload for evaluating a confirmed Mission Contract."""

    profile_id: str = Field(..., description="Identifier of the canonical profile to evaluate.")
    contract: dict[str, Any] = Field(..., description="The confirmed Mission Contract payload.")
    artifact_id: str | None = Field(
        default=None,
        description="Optional CV artifact to evaluate against; defaults to the first CV/resume.",
    )


class EvaluateMissionManyRequest(BaseModel):
    """Request payload for evaluating a contract against several profiles.

    Results are returned together in request order; each candidate keeps its
    individual evidence-backed evaluation from the existing engine.
    """

    profile_ids: list[str] = Field(
        default_factory=list,
        description="Profiles to evaluate, in the order to report results.",
    )
    contract: dict[str, Any] = Field(..., description="The confirmed Mission Contract payload.")


def build_mission_router(
    interpreter: MissionInterpreter | None = None,
    repository: ProfileRepository | None = None,
) -> APIRouter:
    """Create the mission router with lazily-built dependencies.

    ``interpreter`` and ``repository`` may be provided for tests; otherwise
    they are built from the runtime configuration when the first route is hit.
    """
    router = APIRouter(prefix="/missions", tags=["missions"])
    state: dict = {"interpreter": interpreter, "repository": repository}

    def _get_interpreter() -> MissionInterpreter:
        if state["interpreter"] is None:
            state["interpreter"] = MissionInterpreter(provider=create_ai_provider())
        return state["interpreter"]

    def _get_repository() -> ProfileRepository:
        if state["repository"] is None:
            state["repository"] = ProfileRepository(_default_profiles_root())
        return state["repository"]

    def _load_profile(profile_id: str) -> dict[str, Any]:
        try:
            record = _get_repository().get(profile_id)
        except EntityNotFoundError as exc:
            raise _error(404, "NOT_FOUND", str(exc))
        data = record.data
        if not isinstance(data, dict):
            raise _error(500, "INTERNAL_ERROR", "Profile data is malformed.")
        return data

    @router.post("/interpret")
    def interpret_mission(request: InterpretMissionRequest) -> dict[str, Any]:
        """Interpret a natural-language mission into a deterministic Mission Contract."""
        try:
            contract = _get_interpreter().interpret(request.mission)
        except MissionInterpretationError as exc:
            raise _error(422, "INTERPRETATION_FAILED", str(exc))
        return {"contract": contract.to_dict()}

    @router.post("/evaluate-many")
    def evaluate_mission_many_request(request: EvaluateMissionManyRequest) -> dict[str, Any]:
        """Evaluate a confirmed Mission Contract against several profiles."""
        try:
            contract = MissionContract.from_dict(request.contract)
        except MissionContractError as exc:
            raise _error(422, "INVALID_CONTRACT", str(exc))

        ordered = [(profile_id, _load_profile(profile_id)) for profile_id in request.profile_ids]
        try:
            results = evaluate_mission_many(ordered, contract)
        except EntityNotFoundError as exc:
            raise _error(404, "NOT_FOUND", str(exc))
        return {"results": results}

    @router.post("/evaluate")
    def evaluate_mission_request(request: EvaluateMissionRequest) -> dict[str, Any]:
        """Evaluate a confirmed Mission Contract against a canonical profile."""
        try:
            contract = MissionContract.from_dict(request.contract)
        except MissionContractError as exc:
            raise _error(422, "INVALID_CONTRACT", str(exc))

        profile = _load_profile(request.profile_id)
        try:
            result = evaluate_mission(
                profile,
                contract,
                artifact_id=request.artifact_id,
            )
        except EntityNotFoundError as exc:
            raise _error(404, "NOT_FOUND", str(exc))
        return {"result": result.to_dict()}

    return router


MISSION_ROUTER = build_mission_router()

__all__ = ["MISSION_ROUTER", "build_mission_router"]
