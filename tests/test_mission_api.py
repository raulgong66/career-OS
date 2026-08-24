"""API contract tests for the Phase 2 Mission Builder endpoints."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.main import app
from api.routes.mission import build_mission_router
from careeros.ai import MockAIProvider
from careeros.mission import MissionInterpreter
from careeros.mission.contract import _mission_id
from careeros.mission.interpreter import build_prompt
from careeros.profile_repository import ProfileRepository

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[1]
SMITH_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "person-smith-profile.yaml"

MISSION = (
    "We need to stand up a security operations capability for a new managed "
    "security services client who demands real production AWS experience and "
    "proven network security operations."
)

VALID_CONTRACT_PAYLOAD = {
    "summary": "Stand up a managed security services security operations capability.",
    "role": "Security Operations Engineer",
    "requirements": [
        "real production AWS migration experience",
        "network security operations",
    ],
    "capabilities": ["cloud", "threat detection"],
    "evidence_standards": ["real production experience backed by a source document"],
    "constraints": ["managed security services compliance"],
}


def canned_contract_response() -> str:
    return json.dumps(VALID_CONTRACT_PAYLOAD, ensure_ascii=False)


def smith_profile_with_cv_artifact() -> dict[str, Any]:
    data = yaml.safe_load(SMITH_FIXTURE.read_text(encoding="utf-8"))
    data["artifacts"] = [
        {
            "id": "cv-smith",
            "artifactType": "cv",
            "title": "Smith CV",
            "sourceRefs": [],
        }
    ]
    return data


def jones_profile_with_cv_artifact() -> dict[str, Any]:
    data = yaml.safe_load(SMITH_FIXTURE.read_text(encoding="utf-8"))
    data["person"] = {
        **data["person"],
        "id": "person-jones",
        "names": [{"value": "Jordan Jones", "usage": "professional"}],
    }
    data["artifacts"] = [
        {
            "id": "cv-jones",
            "artifactType": "cv",
            "title": "Jones CV",
            "sourceRefs": [],
        }
    ]
    return data


def build_standalone_client(tmp_path: Path, provider: MockAIProvider) -> TestClient:
    """Build a client for a router wired to an isolated repository and provider."""
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir()
    (profiles_root / "person-smith.yaml").write_text(
        yaml.safe_dump(smith_profile_with_cv_artifact(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (profiles_root / "person-jones.yaml").write_text(
        yaml.safe_dump(jones_profile_with_cv_artifact(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    repo = ProfileRepository(profiles_root)
    interpreter = MissionInterpreter(provider=provider)
    standalone = FastAPI()
    standalone.include_router(build_mission_router(interpreter=interpreter, repository=repo))

    @standalone.exception_handler(HTTPException)
    def handle_http_exception(request: Any, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return TestClient(standalone)


def test_interpret_returns_deterministic_contract(tmp_path: Path) -> None:
    provider = MockAIProvider(
        responses={MISSION[:40]: canned_contract_response()},
        default_response=canned_contract_response(),
    )
    api_client = build_standalone_client(tmp_path, provider)

    response = api_client.post("/missions/interpret", json={"mission": MISSION})
    assert response.status_code == 200
    contract = response.json()["contract"]
    assert contract["mission_id"] == _mission_id(MISSION)
    assert contract["mission_statement"] == MISSION
    assert "amazon web services" in contract["requirements"]
    assert "network security" in contract["requirements"]
    assert contract["concepts"]
    assert provider.calls
    assert MISSION in provider.calls[0]


def test_interpret_validation_errors(tmp_path: Path) -> None:
    api_client = build_standalone_client(tmp_path, MockAIProvider())
    response = api_client.post("/missions/interpret", json={"mission": " "})
    assert response.status_code == 422


def test_interpret_failure_is_422(tmp_path: Path) -> None:
    provider = MockAIProvider(fail=True)
    api_client = build_standalone_client(tmp_path, provider)
    response = api_client.post("/missions/interpret", json={"mission": MISSION})
    assert response.status_code == 422
    assert response.json()["error"] == "INTERPRETATION_FAILED"


def test_interpret_invalid_provider_output_is_422(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response="definitely not json")
    api_client = build_standalone_client(tmp_path, provider)
    response = api_client.post("/missions/interpret", json={"mission": MISSION})
    assert response.status_code == 422


def test_evaluate_returns_mission_result(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)

    interpret = api_client.post("/missions/interpret", json={"mission": MISSION})
    contract = interpret.json()["contract"]

    response = api_client.post(
        "/missions/evaluate",
        json={"profile_id": "person-smith", "contract": contract},
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["mission_id"] == contract["mission_id"]
    assert result["status"] in {
        "no_requirements",
        "evidence_gaps",
        "partial_evidence",
        "evidence_backed",
    }
    assert result["requirements"]
    assert 0.0 <= result["text_coverage"] <= 100.0
    assert 0.0 <= result["evidence_backed_coverage"] <= 100.0
    assert result["candidate"]


def test_evaluate_with_unknown_profile_is_404(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)

    response = api_client.post(
        "/missions/evaluate",
        json={
            "profile_id": "no-such-person",
            "contract": {
                "mission_id": _mission_id(MISSION),
                "mission_statement": MISSION,
                "summary": "summary",
                "role": "Security Operations Engineer",
                "requirements": ["network security"],
                "concepts": [],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            },
        },
    )
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_evaluate_rejects_tampered_contract(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)

    contract = {
        "mission_id": "deadbeefdeadbeef",
        "mission_statement": MISSION,
        "summary": "summary",
        "role": "role",
        "requirements": ["network security"],
        "concepts": [],
        "capabilities": [],
        "evidence_standards": [],
        "constraints": [],
    }
    response = api_client.post(
        "/missions/evaluate",
        json={"profile_id": "person-smith", "contract": contract},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "INVALID_CONTRACT"


def _interpreted_contract(api_client: TestClient, provider: MockAIProvider) -> dict[str, Any]:
    interpret = api_client.post("/missions/interpret", json={"mission": MISSION})
    assert interpret.status_code == 200
    return interpret.json()["contract"]


def test_evaluate_many_returns_individual_results_in_order(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)
    contract = _interpreted_contract(api_client, provider)

    response = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": ["person-smith", "person-jones"], "contract": contract},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [entry["profile_id"] for entry in results] == ["person-smith", "person-jones"]
    assert [entry["result"]["candidate"] for entry in results] == ["Jane Smith", "Jordan Jones"]
    for entry in results:
        result = entry["result"]
        assert result["mission_id"] == contract["mission_id"]
        assert result["status"] in {
            "no_requirements",
            "evidence_gaps",
            "partial_evidence",
            "evidence_backed",
        }
        assert result["requirements"]
        assert 0.0 <= result["text_coverage"] <= 100.0
        assert 0.0 <= result["evidence_backed_coverage"] <= 100.0


def test_evaluate_many_uses_the_same_single_candidate_evaluation(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)
    contract = _interpreted_contract(api_client, provider)

    single = api_client.post(
        "/missions/evaluate",
        json={"profile_id": "person-smith", "contract": contract},
    ).json()["result"]
    many = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": ["person-smith"], "contract": contract},
    ).json()["results"]

    assert len(many) == 1
    assert many[0]["profile_id"] == "person-smith"
    assert many[0]["result"] == single


def test_evaluate_many_preserves_request_order(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)
    contract = _interpreted_contract(api_client, provider)

    response = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": ["person-jones", "person-smith"], "contract": contract},
    )
    assert response.status_code == 200
    assert [entry["profile_id"] for entry in response.json()["results"]] == [
        "person-jones",
        "person-smith",
    ]


def test_evaluate_many_empty_selection_is_deterministic(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)
    contract = _interpreted_contract(api_client, provider)

    response = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": [], "contract": contract},
    )
    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_evaluate_many_unknown_profile_is_404(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)
    contract = _interpreted_contract(api_client, provider)

    response = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": ["person-smith", "no-such-person"], "contract": contract},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_evaluate_many_rejects_tampered_contract(tmp_path: Path) -> None:
    provider = MockAIProvider(default_response=canned_contract_response())
    api_client = build_standalone_client(tmp_path, provider)

    contract = {
        "mission_id": "deadbeefdeadbeef",
        "mission_statement": MISSION,
        "summary": "summary",
        "role": "role",
        "requirements": ["network security"],
        "concepts": [],
        "capabilities": [],
        "evidence_standards": [],
        "constraints": [],
    }
    response = api_client.post(
        "/missions/evaluate-many",
        json={"profile_ids": ["person-smith"], "contract": contract},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "INVALID_CONTRACT"


def test_mounted_router_is_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/missions/interpret" in paths
    assert "/missions/evaluate" in paths
    assert "/missions/evaluate-many" in paths
