"""Tests for the provider-neutral Transformation Interpreter."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from careeros.ai import MockAIProvider
from careeros.mission import (
    MissionContract,
    MissionContractError,
    TransformationInterpretationError,
    TransformationInterpreter,
    TransformationPhase,
    TransformationPlan,
)
from careeros.mission.transformation import (
    TruncatedTransformationResponseError,
    _phase_id,
    _plan_id,
    build_prompt,
    parse_response,
)

OBJECTIVE = (
    "Build a production-grade data platform for real-time analytics on AWS "
    "for a healthcare client with HIPAA compliance requirements. The platform "
    "must support 100k events/second, provide sub-second latency, and integrate "
    "with existing clinical data systems."
)

VALID_3_PHASE_PAYLOAD = {
    "summary": "Build a HIPAA-compliant real-time analytics data platform on AWS.",
    "constraints": ["HIPAA compliance", "sub-second latency"],
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
            "constraints": ["sub-second processing latency"],
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


def canned_response(data: dict[str, Any]) -> str:
    import json
    return json.dumps(data, ensure_ascii=False)


def test_plan_id_is_deterministic() -> None:
    a = _plan_id(OBJECTIVE)
    b = _plan_id(OBJECTIVE)
    assert a == b
    assert len(a) == 16


def test_plan_id_differs_for_different_objectives() -> None:
    assert _plan_id(OBJECTIVE) != _plan_id("Completely different objective")


def test_phase_id_is_deterministic() -> None:
    pid = _plan_id(OBJECTIVE)
    a = _phase_id(pid, 1, "Phase One")
    b = _phase_id(pid, 1, "Phase One")
    assert a == b
    assert len(a) == 12


def test_phase_id_differs_for_different_phases() -> None:
    pid = _plan_id(OBJECTIVE)
    assert _phase_id(pid, 1, "Phase One") != _phase_id(pid, 2, "Phase Two")


def test_build_prompt_includes_only_the_objective() -> None:
    prompt = build_prompt(OBJECTIVE)
    assert OBJECTIVE in prompt
    assert '"objective"' in prompt
    assert "evidenceStrength" not in prompt
    assert "weighted_total" not in prompt
    assert '"score"' not in prompt


def test_parse_response_3_phases() -> None:
    plan = parse_response(canned_response(VALID_3_PHASE_PAYLOAD), OBJECTIVE)
    assert plan is not None
    assert isinstance(plan, TransformationPlan)
    assert plan.plan_id == _plan_id(OBJECTIVE)
    assert plan.objective == OBJECTIVE
    assert len(plan.phases) == 3
    assert plan.phases[0].phase_number == 1
    assert plan.phases[1].phase_number == 2
    assert plan.phases[2].phase_number == 3


def test_parse_response_5_phases() -> None:
    payload_5 = {
        "summary": "A 5-phase transformation plan.",
        "constraints": [],
        "phases": [
            {
                "phase_number": i,
                "title": f"Phase {i} title",
                "description": f"Description for phase {i} involving AWS and DevSecOps.",
                "role": "Engineer",
                "requirements": ["real production AWS experience", "DevSecOps"],
                "capabilities": ["cloud"],
                "evidence_standards": [],
                "constraints": [],
            }
            for i in range(1, 6)
        ],
    }
    plan = parse_response(canned_response(payload_5), OBJECTIVE)
    assert plan is not None
    assert len(plan.phases) == 5


def test_parse_response_rejects_2_phases() -> None:
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
    plan = parse_response(canned_response(payload_2), OBJECTIVE)
    assert plan is None


def test_parse_response_rejects_6_phases() -> None:
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
    plan = parse_response(canned_response(payload_6), OBJECTIVE)
    assert plan is None


def test_parse_response_rejects_1_phase() -> None:
    payload_1 = {
        "summary": "Only one phase.",
        "constraints": [],
        "phases": [
            {
                "phase_number": 1,
                "title": "Only phase",
                "description": "One phase with AWS and DevSecOps.",
                "role": "Engineer",
                "requirements": ["real production AWS experience", "DevSecOps"],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            }
        ],
    }
    plan = parse_response(canned_response(payload_1), OBJECTIVE)
    assert plan is None


def test_parse_response_rejects_malformed_payloads() -> None:
    assert parse_response("", OBJECTIVE) is None
    assert parse_response("not json at all", OBJECTIVE) is None
    assert parse_response(canned_response({"summary": "x"}), OBJECTIVE) is None
    assert parse_response(canned_response({"summary": "x", "phases": "not-a-list"}), OBJECTIVE) is None
    assert parse_response(canned_response({"summary": 123, "phases": []}), OBJECTIVE) is None


def test_parse_response_rejects_phase_without_requirements() -> None:
    payload = {
        "summary": "Plan with a bad phase.",
        "constraints": [],
        "phases": [
            {
                "phase_number": 1,
                "title": "Phase 1",
                "description": "Phase with no resolvable requirements.",
                "role": "Engineer",
                "requirements": [],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            },
            {
                "phase_number": 2,
                "title": "Phase 2",
                "description": "Another phase with no resolvable requirements.",
                "role": "Engineer",
                "requirements": [],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            },
            {
                "phase_number": 3,
                "title": "Phase 3",
                "description": "Third phase with no resolvable requirements.",
                "role": "Engineer",
                "requirements": [],
                "capabilities": [],
                "evidence_standards": [],
                "constraints": [],
            },
        ],
    }
    plan = parse_response(canned_response(payload), OBJECTIVE)
    assert plan is None


def test_parse_response_raises_on_truncated_json() -> None:
    truncated = canned_response(VALID_3_PHASE_PAYLOAD)[:-4]
    with pytest.raises(TruncatedTransformationResponseError):
        parse_response(truncated, OBJECTIVE)


def test_parse_response_each_phase_is_valid_mission_contract() -> None:
    plan = parse_response(canned_response(VALID_3_PHASE_PAYLOAD), OBJECTIVE)
    assert plan is not None
    for phase in plan.phases:
        assert isinstance(phase.contract, MissionContract)
        assert phase.contract.mission_id
        assert phase.contract.mission_statement
        assert phase.contract.requirements
        assert phase.contract.concepts


def test_parse_response_preserves_cross_phase_constraints() -> None:
    plan = parse_response(canned_response(VALID_3_PHASE_PAYLOAD), OBJECTIVE)
    assert plan is not None
    assert "HIPAA compliance" in plan.constraints
    assert "sub-second latency" in plan.constraints


def test_parse_response_no_evidence_confidence_scoring() -> None:
    """Interpreter must never produce evidence, confidence, or scoring."""
    plan = parse_response(canned_response(VALID_3_PHASE_PAYLOAD), OBJECTIVE)
    assert plan is not None
    raw = plan.to_dict()
    raw_str = str(raw)
    for forbidden in ["evidence_strength", "confidence_score", "candidate_score", "weighted_total"]:
        assert forbidden not in raw_str


def test_plan_round_trip() -> None:
    plan = parse_response(canned_response(VALID_3_PHASE_PAYLOAD), OBJECTIVE)
    assert plan is not None
    rebuilt = TransformationPlan.from_dict(plan.to_dict())
    assert rebuilt == plan


def test_plan_from_dict_rejects_invalid() -> None:
    with pytest.raises(MissionContractError):
        TransformationPlan.from_dict(None)
    with pytest.raises(MissionContractError):
        TransformationPlan.from_dict({"plan_id": "", "objective": "x", "summary": "s", "phases": []})
    with pytest.raises(MissionContractError):
        TransformationPlan.from_dict({"plan_id": "abc", "objective": "", "summary": "s", "phases": []})


def test_phase_from_dict_rejects_invalid() -> None:
    with pytest.raises(MissionContractError):
        TransformationPhase.from_dict(None)
    with pytest.raises(MissionContractError):
        TransformationPhase.from_dict({"phase_id": "", "phase_number": 1, "title": "x", "description": "y", "contract": {}})


def test_interpreter_returns_plan_from_mock_provider() -> None:
    provider = MockAIProvider(
        responses={OBJECTIVE[:40]: canned_response(VALID_3_PHASE_PAYLOAD)},
        default_response=canned_response(VALID_3_PHASE_PAYLOAD),
    )
    interpreter = TransformationInterpreter(provider=provider)
    plan = interpreter.interpret(OBJECTIVE)
    assert isinstance(plan, TransformationPlan)
    assert plan.plan_id == _plan_id(OBJECTIVE)
    assert provider.calls
    assert OBJECTIVE in provider.calls[0]


def test_interpreter_surfaces_provider_failures() -> None:
    provider = MockAIProvider(fail=True)
    interpreter = TransformationInterpreter(provider=provider)
    with pytest.raises(TransformationInterpretationError):
        interpreter.interpret(OBJECTIVE)


def test_interpreter_rejects_invalid_provider_output() -> None:
    provider = MockAIProvider(default_response="no json here")
    interpreter = TransformationInterpreter(provider=provider)
    with pytest.raises(TransformationInterpretationError):
        interpreter.interpret(OBJECTIVE)


def test_interpreter_rejects_truncated_provider_output() -> None:
    provider = MockAIProvider(default_response=canned_response(VALID_3_PHASE_PAYLOAD)[:-2])
    interpreter = TransformationInterpreter(provider=provider)
    with pytest.raises(TransformationInterpretationError):
        interpreter.interpret(OBJECTIVE)


def test_interpreter_rejects_empty_objective() -> None:
    interpreter = TransformationInterpreter(provider=MockAIProvider())
    with pytest.raises(TransformationInterpretationError):
        interpreter.interpret("   ")


def test_interpreter_each_phase_contract_has_requirements() -> None:
    provider = MockAIProvider(default_response=canned_response(VALID_3_PHASE_PAYLOAD))
    interpreter = TransformationInterpreter(provider=provider)
    plan = interpreter.interpret(OBJECTIVE)
    for phase in plan.phases:
        assert phase.contract.requirements
        assert len(phase.contract.concepts) > 0


def test_interpreter_cross_phase_constraints_preserved() -> None:
    provider = MockAIProvider(default_response=canned_response(VALID_3_PHASE_PAYLOAD))
    interpreter = TransformationInterpreter(provider=provider)
    plan = interpreter.interpret(OBJECTIVE)
    assert "HIPAA compliance" in plan.constraints
    assert "sub-second latency" in plan.constraints
