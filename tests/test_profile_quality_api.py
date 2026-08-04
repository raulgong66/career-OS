"""API contract tests for the M1.24.2 Profile Quality endpoints."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.main import app
from api.routes.profile_quality import build_profile_quality_router
from careeros.profile_quality.cli import profile_health_data
from careeros.profile_quality.engine import run_profile_quality
from careeros.profile_quality.unified import (
    filter_and_sort_recommendations,
    to_unified_recommendations,
)
from careeros.profile_repository import ProfileRepository

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROFILE_ID = "raul-gongora-profile"
SAMPLE_PROFILE_FILE = REPO_ROOT / "profiles" / f"{SAMPLE_PROFILE_ID}.yaml"

REPORT_KEYS = {"health_score", "dimensions", "findings", "citations"}
RECOMMENDATION_KEYS = {
    "id",
    "source",
    "rule_id",
    "element_id",
    "element_type",
    "title",
    "reason",
    "suggested_action",
    "resolution_type",
    "evidence_refs",
    "priority",
    "estimated_impact",
    "confidence",
    "jd_match_score",
    "context_match_score",
    "weighted_total",
}


def sample_profile() -> dict[str, Any]:
    return yaml.safe_load(SAMPLE_PROFILE_FILE.read_text(encoding="utf-8"))


def cli_quality_report() -> dict[str, Any]:
    return profile_health_data(sample_profile())


def cli_improvement_queue() -> list[dict[str, Any]]:
    report = run_profile_quality(sample_profile())
    recommendations = filter_and_sort_recommendations(
        to_unified_recommendations(report),
    )
    return [recommendation.to_dict() for recommendation in recommendations]


def build_standalone_client(profiles_root: Path) -> TestClient:
    """Build a client for a router wired to an isolated profile repository."""
    repo = ProfileRepository(profiles_root)
    standalone = FastAPI()
    standalone.include_router(build_profile_quality_router(repository=repo))

    @standalone.exception_handler(HTTPException)
    def handle_http_exception(request: Any, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return TestClient(standalone)


def test_quality_report_endpoint() -> None:
    """GET /profiles/{id}/quality-report returns a full, valid health report."""
    response = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/quality-report")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == REPORT_KEYS
    assert isinstance(body["health_score"], int)
    assert 0 <= body["health_score"] <= 100
    assert isinstance(body["dimensions"], list)
    assert len(body["dimensions"]) == 8
    for dimension in body["dimensions"]:
        assert {"name", "score", "weight"} <= set(dimension.keys())
        assert 0.0 <= dimension["score"] <= 1.0
    assert isinstance(body["findings"], list)
    assert isinstance(body["citations"], list)


def test_quality_report_matches_cli_contract() -> None:
    """REST quality-report matches the CLI profile-health JSON structure (AC 1.8)."""
    response = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/quality-report")
    assert response.status_code == 200
    assert response.json() == cli_quality_report()


def test_quality_report_citations_are_well_formed() -> None:
    """Every citation carries deterministic evidence references."""
    body = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/quality-report").json()
    for citation in body["citations"]:
        assert {"entity_id", "entity_type", "property_path", "snippet"} <= set(citation.keys())
        assert citation["entity_id"]
        assert citation["entity_type"]


def test_quality_report_is_deterministic() -> None:
    """Repeated calls return byte-identical reports."""
    first = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/quality-report")
    second = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/quality-report")
    assert first.status_code == 200
    assert first.json() == second.json()


def test_quality_report_profile_not_found() -> None:
    """GET /profiles/{id}/quality-report returns 404 for a non-existent profile."""
    response = client.get("/profiles/non-existent-profile/quality-report")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_quality_report_invalid_profile_id() -> None:
    """GET /profiles/{id}/quality-report rejects a malformed profile id."""
    response = client.get("/profiles/not!a!valid~id/quality-report")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_improvement_queue_endpoint() -> None:
    """GET /profiles/{id}/improvement-queue returns unified recommendations."""
    response = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for item in body:
        assert set(item.keys()) == RECOMMENDATION_KEYS
        assert item["source"] == "profile_quality"
        assert item["resolution_type"] in {"auto", "guided", "none"}
        assert item["priority"] in {"high", "medium", "low"}
        assert isinstance(item["evidence_refs"], list)


def test_improvement_queue_matches_cli_contract() -> None:
    """REST improvement-queue matches the CLI improvement-queue JSON structure (AC 1.9)."""
    response = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue")
    assert response.status_code == 200
    assert response.json() == cli_improvement_queue()


def test_improvement_queue_filter_by_priority() -> None:
    """?priority= filters the queue to matching items."""
    response = client.get(
        f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue",
        params={"priority": "high"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["priority"] == "high" for item in body)


def test_improvement_queue_filter_by_resolution_type() -> None:
    """?resolution_type= filters the queue to matching items."""
    response = client.get(
        f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue",
        params={"resolution_type": "auto"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["resolution_type"] == "auto" for item in body)


def test_improvement_queue_is_deterministic() -> None:
    """Repeated calls return byte-identical queues."""
    first = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue")
    second = client.get(f"/profiles/{SAMPLE_PROFILE_ID}/improvement-queue")
    assert first.status_code == 200
    assert first.json() == second.json()


def test_improvement_queue_profile_not_found() -> None:
    """GET /profiles/{id}/improvement-queue returns 404 for a non-existent profile."""
    response = client.get("/profiles/non-existent-profile/improvement-queue")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_empty_profile_returns_valid_report(tmp_path: Path) -> None:
    """An empty canonical profile yields a valid report, not an error."""
    (tmp_path / "empty.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    standalone = build_standalone_client(tmp_path)

    report = standalone.get("/profiles/empty/quality-report")
    assert report.status_code == 200
    body = report.json()
    assert set(body.keys()) == REPORT_KEYS
    assert 0 <= body["health_score"] <= 100

    queue = standalone.get("/profiles/empty/improvement-queue")
    assert queue.status_code == 200
    assert isinstance(queue.json(), list)


def test_malformed_profile_returns_500(tmp_path: Path) -> None:
    """A non-dict profile payload surfaces a consistent 500 error."""
    (tmp_path / "malformed.yaml").write_text("- not\n- a\n- dict\n", encoding="utf-8")
    standalone = build_standalone_client(tmp_path)

    report = standalone.get("/profiles/malformed/quality-report")
    assert report.status_code == 500
    assert report.json()["error"] == "INTERNAL_ERROR"

    queue = standalone.get("/profiles/malformed/improvement-queue")
    assert queue.status_code == 500
    assert queue.json()["error"] == "INTERNAL_ERROR"
