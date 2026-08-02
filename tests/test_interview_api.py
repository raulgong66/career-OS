"""M1.18 — Interview Simulation API tests.

Covers the interview session endpoints proposed in
``docs/platform-beta/interview-simulation/05-api-proposal.md``: create, submit
answer (with immediate evaluation markers), next, pause/resume, get session,
and report. The API layer is thin transport/orchestration: it reuses the
stateless ``SessionEngine`` and ``EvaluationEngine`` and never re-implements
evaluation or sequencing policy.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)

SAMPLE_PROFILE = "raul-gongora-profile"

EVALUATION_SIGNALS = {
    "covers_claim",
    "has_metric",
    "cites_evidence",
    "follows_structure",
    "matches_question_competencies",
    "citations",
}


def _create_session(target_role: str | None = "Platform Engineer") -> dict:
    payload: dict = {"profile_id": SAMPLE_PROFILE}
    if target_role is not None:
        payload["target_role"] = target_role
    response = client.post("/interviews/sessions", json=payload)
    assert response.status_code == 201
    return response.json()


def _advance(session_id: str) -> dict:
    response = client.post(f"/interviews/sessions/{session_id}/next")
    assert response.status_code == 200
    return response.json()


def _submit_answer(session_id: str, text: str, duration_seconds: int | None = None) -> dict:
    payload: dict = {"text": text}
    if duration_seconds is not None:
        payload["duration_seconds"] = duration_seconds
    response = client.post(f"/interviews/sessions/{session_id}/answers", json=payload)
    assert response.status_code == 200
    return response.json()


STRONG_ANSWER = (
    "As a Platform Engineer at ACME Corp I was responsible for the Kubernetes "
    "migration. I led the migration of 200 services, which reduced "
    "infrastructure costs by 40% as a result."
)


# --------------------------------------------------------------------------
# create
# --------------------------------------------------------------------------


def test_create_session_returns_started_session() -> None:
    session = _create_session()
    assert session["id"].startswith("interview-")
    assert session["state"] == "in_progress"
    assert session["profile_id"] == "person-raul-gongora"
    assert session["plan_ref"]
    assert len(session["questions"]) >= 1
    first = session["questions"][0]
    assert first["question_text"]
    assert first["category"]
    assert isinstance(first["context_refs"], list)


def test_create_session_without_target_role() -> None:
    session = _create_session(target_role=None)
    assert session["state"] == "in_progress"
    assert len(session["questions"]) >= 1


def test_create_session_missing_profile_is_404() -> None:
    response = client.post(
        "/interviews/sessions",
        json={"profile_id": "does-not-exist"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


# --------------------------------------------------------------------------
# next
# --------------------------------------------------------------------------


def test_next_returns_active_question() -> None:
    session = _create_session()
    payload = _advance(session["id"])
    assert payload["completed"] is False
    question = payload["question"]
    assert question["question_text"]
    assert question["category"]
    assert question["session_id"] == session["id"]
    assert "evidence_citations" in question


# --------------------------------------------------------------------------
# answers / evaluation markers
# --------------------------------------------------------------------------


def test_submit_answer_records_evaluation_and_feedback() -> None:
    session = _create_session()
    _advance(session["id"])
    payload = _submit_answer(session["id"], STRONG_ANSWER, duration_seconds=75)
    answer = payload["answer"]
    assert answer["session_id"] == session["id"]
    assert answer["text"] == STRONG_ANSWER
    assert answer["duration_seconds"] == 75

    evaluation = answer["evaluation"]
    assert EVALUATION_SIGNALS == set(evaluation)
    assert isinstance(evaluation["covers_claim"], bool)
    assert isinstance(evaluation["has_metric"], bool)

    feedback = answer["feedback"]
    assert feedback["answer_id"] == answer["id"]
    assert isinstance(feedback["missing"], list)

    assert len(payload["session"]["answers"]) == 1


def test_submit_answer_rejects_empty_text() -> None:
    session = _create_session()
    _advance(session["id"])
    response = client.post(
        f"/interviews/sessions/{session['id']}/answers",
        json={"text": "   "},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "INVALID_ANSWER"


def test_submit_answer_when_exhausted_is_409() -> None:
    session = _create_session()
    for _ in session["questions"]:
        _advance(session["id"])
        _submit_answer(session["id"], STRONG_ANSWER)
    response = client.post(
        f"/interviews/sessions/{session['id']}/answers",
        json={"text": STRONG_ANSWER},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "NO_ACTIVE_QUESTION"


# --------------------------------------------------------------------------
# completion + report
# --------------------------------------------------------------------------


def test_next_after_last_answer_completes_and_builds_report() -> None:
    session = _create_session()
    question_count = len(session["questions"])
    for _ in session["questions"]:
        _advance(session["id"])
        _submit_answer(session["id"], STRONG_ANSWER)

    payload = _advance(session["id"])
    assert payload["completed"] is True
    assert payload["session"]["state"] == "completed"
    assert payload["session"]["summary"]["answered_questions"] == question_count

    report = payload["report"]
    assert report["session_id"] == session["id"]
    assert report["summary"]["total_questions"] == question_count
    assert isinstance(report["strengths"], list)
    assert isinstance(report["weaknesses"], list)
    assert isinstance(report["recommendations"], list)


def test_report_endpoint_returns_report_after_completion() -> None:
    session = _create_session()
    for _ in session["questions"]:
        _advance(session["id"])
        _submit_answer(session["id"], STRONG_ANSWER)
    _advance(session["id"])

    response = client.get(f"/interviews/sessions/{session['id']}/report")
    assert response.status_code == 200
    report = response.json()
    assert report["id"] == f"{session['id']}:report"
    assert report["summary"]["answered_questions"] == len(session["questions"])
    assert report["session_metrics"]["answered_questions"] == len(session["questions"])


def test_report_before_completion_is_409() -> None:
    session = _create_session()
    response = client.get(f"/interviews/sessions/{session['id']}/report")
    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_STATE"


# --------------------------------------------------------------------------
# get / pause / resume
# --------------------------------------------------------------------------


def test_get_session_returns_state() -> None:
    session = _create_session()
    response = client.get(f"/interviews/sessions/{session['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == session["id"]
    assert response.json()["state"] == "in_progress"


def test_get_missing_session_is_404() -> None:
    response = client.get("/interviews/sessions/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_pause_and_resume() -> None:
    session = _create_session()
    paused = client.post(f"/interviews/sessions/{session['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["state"] == "paused"

    resumed = client.post(f"/interviews/sessions/{session['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["state"] == "in_progress"


def test_pause_invalid_state_is_409() -> None:
    session = _create_session()
    client.post(f"/interviews/sessions/{session['id']}/pause")
    second = client.post(f"/interviews/sessions/{session['id']}/pause")
    assert second.status_code == 409
    assert second.json()["error"] == "INVALID_STATE"
