"""Transformation Mission API routes.

Mounted into the main FastAPI app from ``api/main.py``. The router is
transport-only: it interprets a client objective through the provider-neutral
transformation interpreter and returns deterministic serialized outputs.

The human confirmation step and phase selection are frontend concerns. The
existing Mission evaluation pipeline handles all downstream evaluation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from careeros.ai import create_ai_provider
from careeros.mission.transformation import (
    TransformationInterpretationError,
    TransformationInterpreter,
)


def _default_profiles_root() -> Path:
    return Path(__file__).resolve().parents[2] / "profiles"


def _error(status_code: int, error: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "detail": detail})


class InterpretTransformationRequest(BaseModel):
    """Request payload for interpreting a client objective into a plan."""

    objective: str = Field(..., min_length=1, description="Client business objective in natural language.")


def build_transformation_router(
    interpreter: TransformationInterpreter | None = None,
) -> APIRouter:
    """Create the transformation router with lazily-built dependencies."""
    router = APIRouter(prefix="/transformations", tags=["transformations"])
    state: dict = {"interpreter": interpreter}

    def _get_interpreter() -> TransformationInterpreter:
        if state["interpreter"] is None:
            state["interpreter"] = TransformationInterpreter(provider=create_ai_provider())
        return state["interpreter"]

    @router.post("/interpret")
    def interpret_transformation(request: InterpretTransformationRequest) -> dict[str, Any]:
        """Interpret a client objective into a deterministic Transformation Plan."""
        try:
            plan = _get_interpreter().interpret(request.objective)
        except TransformationInterpretationError as exc:
            raise _error(422, "INTERPRETATION_FAILED", str(exc))
        return {"plan": plan.to_dict()}

    return router


TRANSFORMATION_ROUTER = build_transformation_router()

__all__ = ["TRANSFORMATION_ROUTER", "build_transformation_router"]
