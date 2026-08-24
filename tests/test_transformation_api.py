"""API contract tests for the Transformation Mission endpoints."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.main import app
from api.routes.transformation import build_transformation_router
from careeros.ai import MockAIProvider
from careeros.mission.transformation import (
    TransformationInterpreter,
    _plan_id,
)

client = TestClient(app)

OBJECTIVE = (
    "Build a production-grade data platform for real-time analytics on AWS "
    "for a healthcare client with HIPAA compliance requirements."
)

VALID_3_PHASE_PAYLOAD = {
    "summary": "Build a HIPAA-compliant real-time analytics data platform on AWS.",
    "constraints": ["HIPAA compliance"],
    "phases": [
        {
            "phase_number": 1,
            "title": "Cloud Infrastructure & Security Foundation",
            "description": "Stand up HIPAA-eligible AWS infrastructure with networking, IAM, and audit logging.",
            "role": "Cloud Security Engineer",
            "requirements": ["real production AWS experience", "DevSecOps", "cloud security"],
            "capabilities": ["cloud", "security"],
            "evidence_standards": ["production AWS deployment"],
            "constraints": ["HIPAA audit logging"],
        },
        {
            "phase_number": 2,
            "title": "Data Ingestion Pipeline",
            "description": "Build a real-time data ingestion pipeline handling 100k events per second.",
            "role": "Data Engineer",
            "requirements": ["data pipelines", "data engineering", "kubernetes"],
            "capabilities": ["streaming", "data engineering"],
            "evidence_standards": ["production streaming pipeline"],
            "constraints": [],
        },
        {
            "phase_number": 3,
            "title": "Analytics & Machine Learning Layer",
            "description": "Deploy analytics and machine learning models with real-time scoring.",
            "role": "ML Engineer",
            "requirements": ["machine learning", "python", "monitoring"],
            "capabilities": ["analytics", "machine learning"],
            "evidence_standards": ["production ML platform"],
            "constraints": [],
        },
    ],
}


def canned_response() -> str:
    return json.dumps(VALID_3_PHASE_PAYLOAD, ensure_ascii=False)


def build_standalone_client(provider: MockAIProvider) -> TestClient:
    """Build a client for a transformation router wired to an isolated provider."""
    interpreter = TransformationInterpreter(provider=provider)
    standalone = FastAPI()
    standalone.include_router(build_transformation_router(interpreter=interpreter))

    @standalone.exception_handler(HTTPException)
    def handle_http_exception(request: Any, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return TestClient(standalone)


def test_interpret_returns_valid_plan() -> None:
    provider = MockAIProvider(
        responses={OBJECTIVE[:40]: canned_response()},
        default_response=canned_response(),
    )
    api_client = build_standalone_client(provider)

    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["plan_id"] == _plan_id(OBJECTIVE)
    assert plan["objective"] == OBJECTIVE
    assert len(plan["phases"]) == 3
    assert plan["constraints"]
    assert provider.calls
    assert OBJECTIVE in provider.calls[0]


def test_interpret_each_phase_has_valid_contract() -> None:
    provider = MockAIProvider(default_response=canned_response())
    api_client = build_standalone_client(provider)

    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 200
    for phase in response.json()["plan"]["phases"]:
        assert "phase_id" in phase
        assert "contract" in phase
        contract = phase["contract"]
        assert contract["mission_id"]
        assert contract["mission_statement"]
        assert contract["requirements"]
        assert contract["concepts"]
        assert 0 < len(contract["requirements"])


def test_interpret_validation_errors() -> None:
    api_client = build_standalone_client(MockAIProvider())
    response = api_client.post("/transformations/interpret", json={"objective": " "})
    assert response.status_code == 422


def test_interpret_missing_objective() -> None:
    api_client = build_standalone_client(MockAIProvider())
    response = api_client.post("/transformations/interpret", json={})
    assert response.status_code == 422


def test_interpret_failure_is_422() -> None:
    provider = MockAIProvider(fail=True)
    api_client = build_standalone_client(provider)
    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 422
    assert response.json()["error"] == "INTERPRETATION_FAILED"


def test_interpret_invalid_provider_output_is_422() -> None:
    provider = MockAIProvider(default_response="definitely not json")
    api_client = build_standalone_client(provider)
    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 422


def test_interpret_2_phases_is_422() -> None:
    payload_2 = {
        "summary": "Only 2 phases.",
        "constraints": [],
        "phases": [
            {
                "phase_number": i,
                "title": f"Phase {i}",
                "description": f"Description for phase {i} involving AWS and DevSecOps.",
                "role": "Engineer",
                "requirements": ["real production AWS experience", "DevSecOps"],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            }
            for i in range(1, 3)
        ],
    }
    provider = MockAIProvider(default_response=json.dumps(payload_2))
    api_client = build_standalone_client(provider)
    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 422
    assert response.json()["error"] == "INTERPRETATION_FAILED"


def test_interpret_6_phases_is_422() -> None:
    payload_6 = {
        "summary": "Too many phases.",
        "constraints": [],
        "phases": [
            {
                "phase_number": i,
                "title": f"Phase {i}",
                "description": f"Description for phase {i} involving AWS and DevSecOps.",
                "role": "Engineer",
                "requirements": ["real production AWS experience", "DevSecOps"],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            }
            for i in range(1, 7)
        ],
    }
    provider = MockAIProvider(default_response=json.dumps(payload_6))
    api_client = build_standalone_client(provider)
    response = api_client.post("/transformations/interpret", json={"objective": OBJECTIVE})
    assert response.status_code == 422


def test_mounted_router_is_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/transformations/interpret" in paths
