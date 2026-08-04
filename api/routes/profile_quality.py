"""Profile Quality API routes (M1.24.2).

Mounted into the main FastAPI app from ``api/main.py``. The router is
transport-only (ADR-009, architecture guardrails): it loads the canonical
profile and returns the deterministic serialized outputs produced by
``careeros.profile_quality``. No scoring, reasoning, deduplication, or
business rules live here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from careeros.exceptions import EntityNotFoundError
from careeros.profile_quality.cli import profile_health_data
from careeros.profile_quality.engine import run_profile_quality
from careeros.profile_quality.unified import (
    filter_and_sort_recommendations,
    to_unified_recommendations,
)
from careeros.profile_repository import ProfileRepository


def _default_profiles_root() -> Path:
    """Resolve the canonical profiles directory relative to this package."""
    return Path(__file__).resolve().parents[2] / "profiles"


def _error(status_code: int, error: str, detail: str) -> HTTPException:
    """Build a consistent API error response (matches ``ApiErrorResponse``)."""
    return HTTPException(status_code=status_code, detail={"error": error, "detail": detail})


def build_profile_quality_router(repository: ProfileRepository | None = None) -> APIRouter:
    """Create the profile-quality router with a lazily-built profile repository.

    ``repository`` may be provided for tests; otherwise a repository is built
    against the canonical profiles directory when the first route is hit.
    """
    router = APIRouter(prefix="/profiles", tags=["profiles"])
    state: dict = {"repository": repository}

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

    @router.get("/{profile_id}/quality-report", response_model=dict[str, Any])
    def profile_quality_report(profile_id: str) -> dict[str, Any]:
        """Return the deterministic profile quality report for a profile."""
        return profile_health_data(_load_profile(profile_id))

    @router.get("/{profile_id}/improvement-queue", response_model=list[dict[str, Any]])
    def profile_improvement_queue(
        profile_id: str,
        priority: str | None = Query(None, description="Filter by priority (high|medium|low)."),
        resolution_type: str | None = Query(
            None,
            description="Filter by resolution type (auto|guided|none).",
        ),
    ) -> list[dict[str, Any]]:
        """Return the filterable unified recommendation queue for a profile."""
        report = run_profile_quality(_load_profile(profile_id))
        recommendations = filter_and_sort_recommendations(
            to_unified_recommendations(report),
            priority=priority,
            resolution_type=resolution_type,
        )
        return [recommendation.to_dict() for recommendation in recommendations]

    return router


PROFILE_QUALITY_ROUTER = build_profile_quality_router()

__all__ = ["PROFILE_QUALITY_ROUTER", "build_profile_quality_router"]
