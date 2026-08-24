"""Tests for the provider-neutral Mission Interpreter and Mission Contract."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from careeros.ai import MockAIProvider
from careeros.mission import (
    MissionContract,
    MissionContractError,
    MissionInterpretationError,
    MissionInterpreter,
    TruncatedMissionResponseError,
    build_contract,
)
from careeros.mission.contract import _mission_id
from careeros.mission.interpreter import build_prompt, parse_response
from careeros.optimizer import CONCEPT_TAXONOMY

MISSION = (
    "We need to stand up a security operations capability for a new "
    "managed security services client who demands real production AWS "
    "experience and proven network security operations."
)

VALID_RESPONSE = {
    "summary": "Stand up a managed security services security operations capability.",
    "role": "Security Operations Engineer",
    "requirements": [
        "real production AWS migration experience",
        "network security operations",
    ],
    "capabilities": ["cloud", "threat detection"],
    "evidence_standards": [
        "real production experience backed by a source document",
    ],
    "constraints": ["managed security services compliance"],
}

CONCEPT_IDS = {concept.id for concept in CONCEPT_TAXONOMY}


def canned_response(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False)


def test_build_prompt_includes_only_the_mission() -> None:
    prompt = build_prompt(MISSION)
    assert MISSION in prompt
    assert '"mission"' in prompt
    assert "evidenceStrength" not in prompt
    assert "weighted_total" not in prompt
    assert '"score"' not in prompt


def test_parse_response_builds_deterministic_contract() -> None:
    contract = parse_response(canned_response(VALID_RESPONSE), MISSION)
    assert contract is not None
    assert contract.mission_statement == MISSION
    assert contract.mission_id == _mission_id(MISSION)
    assert contract.requirements
    assert "amazon web services" in contract.requirements
    assert "network security" in contract.requirements
    assert set(contract.concepts) <= CONCEPT_IDS


def test_parse_response_rejects_malformed_payloads() -> None:
    assert parse_response("", MISSION) is None
    assert parse_response("not json at all", MISSION) is None
    assert parse_response(canned_response({"role": "x"}), MISSION) is None
    assert parse_response(canned_response(VALID_RESPONSE | {"requirements": "not-a-list"}), MISSION) is None
    assert parse_response(canned_response(VALID_RESPONSE | {"capabilities": 5}), MISSION) is None
    assert parse_response(canned_response(VALID_RESPONSE | {"summary": 123}), MISSION) is None


def test_parse_response_raises_on_truncated_json() -> None:
    truncated = canned_response(VALID_RESPONSE)[:-4]
    with pytest.raises(TruncatedMissionResponseError):
        parse_response(truncated, MISSION)


def test_interpreter_returns_contract_from_mock_provider() -> None:
    provider = MockAIProvider(
        responses={MISSION[:40]: canned_response(VALID_RESPONSE)},
        default_response=canned_response(VALID_RESPONSE),
    )
    interpreter = MissionInterpreter(provider=provider)
    contract = interpreter.interpret(MISSION)
    assert isinstance(contract, MissionContract)
    assert contract.mission_id == _mission_id(MISSION)
    assert provider.calls
    assert MISSION in provider.calls[0]


def test_interpreter_surfaces_provider_failures() -> None:
    provider = MockAIProvider(fail=True)
    interpreter = MissionInterpreter(provider=provider)
    with pytest.raises(MissionInterpretationError):
        interpreter.interpret(MISSION)


def test_interpreter_rejects_invalid_provider_output() -> None:
    provider = MockAIProvider(default_response="no json here")
    interpreter = MissionInterpreter(provider=provider)
    with pytest.raises(MissionInterpretationError):
        interpreter.interpret(MISSION)


def test_interpreter_rejects_truncated_provider_output() -> None:
    provider = MockAIProvider(default_response=canned_response(VALID_RESPONSE)[:-2])
    interpreter = MissionInterpreter(provider=provider)
    with pytest.raises(MissionInterpretationError):
        interpreter.interpret(MISSION)


def test_interpreter_rejects_empty_mission() -> None:
    interpreter = MissionInterpreter(provider=MockAIProvider())
    with pytest.raises(MissionInterpretationError):
        interpreter.interpret("   ")


def test_build_contract_validation() -> None:
    with pytest.raises(MissionContractError):
        build_contract("", "summary", "role", ["aws"])
    with pytest.raises(MissionContractError):
        build_contract("mission", "", "role", ["aws"])
    with pytest.raises(MissionContractError):
        build_contract("mission", "summary", "", ["aws"])
    with pytest.raises(MissionContractError):
        build_contract("mission", "summary", "role", ["aws"] * 26)
    with pytest.raises(MissionContractError):
        build_contract("mission", "summary", "role", [])
    with pytest.raises(MissionContractError):
        build_contract("mission", "summary", "role", ["aws", 1])


def test_build_contract_normalizes_through_optimizer_pipeline() -> None:
    contract = build_contract(
        MISSION,
        "Stand up managed security services.",
        "Security Operations Engineer",
        ["AWS experience", "network security"],
        capabilities=["cloud"],
        constraints=["compliance"],
    )
    assert contract.mission_id == _mission_id(MISSION)
    assert "amazon web services" in contract.requirements
    assert "network security" in contract.requirements
    assert contract.concepts


def test_contract_round_trip_and_integrity() -> None:
    contract = build_contract(
        MISSION,
        "Stand up managed security services.",
        "Security Operations Engineer",
        ["AWS experience", "network security"],
        capabilities=["cloud"],
    )
    rebuilt = MissionContract.from_dict(contract.to_dict())
    assert rebuilt == contract

    tampered = contract.to_dict()
    tampered["mission_id"] = hashlib.sha256(b"tampered").hexdigest()[:16]
    with pytest.raises(MissionContractError):
        MissionContract.from_dict(tampered)

    with pytest.raises(MissionContractError):
        MissionContract.from_dict(None)
    with pytest.raises(MissionContractError):
        MissionContract.from_dict(contract.to_dict() | {"requirements": [1]})
