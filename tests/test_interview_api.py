"""Interview Simulation API contract tests (M1.19 Phase 2).

The API layer is transport-only: these tests verify session orchestration,
DTO shapes, evidence reference preservation (``{id, type}``), and domain
exception translation into HTTP responses.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_profile() -> dict:
    """A canonical profile that yields a non-empty, evidence-backed plan."""
    return {
        "profileVersion": "1.0.0",
        "person": {"id": "person-tester", "names": [{"value": "Test Person"}]},
        "experiences": [
            {
                "id": "exp-1",
                "title": "Platform Engineer",
                "scope": "Built a scalable platform and reduced costs by 30%.",
            }
        ],
        "skills": [
            {
                "id": "skill-1",
                "name": "Kubernetes",
                "extensions": {"experienceEvidence": [{"experienceId": "exp-1"}]},
            }
        ],
        "projects": [],
        "achievements": [],
        "education": [],
        "certifications": [],
    }


def create_session() -> dict:
    response = client.post("/interviews/sessions", json={"profile": make_profile()})
    assert response.status_code == 201, response.text
    return response.json()


def active_question(session_id: str) -> dict:
    session = client.get(f"/interviews/sessions/{session_id}").json()
    return session["current_question"]


def answer_payload(
    current_question: dict,
    *,
    text: str | None = None,
    refs: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "question_id": current_question["question"]["id"],
        "text": text if text is not None else (
            "I led the design and implementation of a platform service, deployed it "
            "to production, and reduced costs by 30%. I measured the impact and "
            "delivered the outcome."
        ),
        "evidence_references": (
            refs if refs is not None else current_question["question"]["evidence_citations"]
        ),
    }


def submit_answer(session_id: str, payload: dict) -> dict:
    response = client.post(f"/interviews/sessions/{session_id}/answers", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def complete_session(session_id: str) -> None:
    """Answer every question and advance until the session completes."""
    for _ in range(50):
        session = client.get(f"/interviews/sessions/{session_id}").json()
        if session["state"] == "completed":
            return
        current = session["current_question"]
        assert current is not None, session
        submit_answer(session_id, answer_payload(current))
        advance = client.post(f"/interviews/sessions/{session_id}/next")
        assert advance.status_code == 200, advance.text


class TestCreateSession:

    def test_creates_and_starts_session(self) -> None:
        session = create_session()
        assert session["session_id"]
        assert session["profile_id"] == "person-tester"
        assert session["state"] == "in_progress"
        assert session["question_count"] > 0
        assert session["answered_count"] == 0
        assert session["current_question_index"] == 0
        current = session["current_question"]
        assert current["index"] == 1
        assert current["total"] == session["question_count"]
        assert current["question"]["id"]
        assert current["question"]["text"]

    def test_preserves_evidence_references_as_id_type(self) -> None:
        session = create_session()
        citations = session["current_question"]["question"]["evidence_citations"]
        assert citations
        for ref in citations:
            assert set(ref) == {"id", "type"}
        assert "profileVersion" not in str(session)

    def test_missing_profile_returns_422(self) -> None:
        response = client.post("/interviews/sessions", json={})
        assert response.status_code == 422

    def test_non_dict_profile_returns_422(self) -> None:
        response = client.post("/interviews/sessions", json={"profile": "not-a-profile"})
        assert response.status_code == 422


class TestSubmitAnswer:

    def test_records_answer_and_returns_evaluation_signals(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        result = submit_answer(session_id, answer_payload(current))
        assert result["session"]["answered_count"] == 1
        assert result["session"]["state"] == "in_progress"
        evaluation = result["evaluation"]
        assert evaluation["question_id"] == current["question"]["id"]
        for score in (
            evaluation["coverage_score"],
            evaluation["evidence_score"],
            evaluation["structure_score"],
            evaluation["overall_score"],
        ):
            assert 0 <= score <= 100
        assert isinstance(evaluation["feedback"], list)
        answer = result["session"]["answers"][0]
        assert answer["question_id"] == current["question"]["id"]
        assert answer["evidence_references"] == current["question"]["evidence_citations"]

    def test_wrong_question_id_returns_409(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        payload = answer_payload(current)
        payload["question_id"] = "wrong-question"
        response = client.post(f"/interviews/sessions/{session_id}/answers", json=payload)
        assert response.status_code == 409
        assert response.json()["error"] == "INVALID_QUESTION"

    def test_empty_answer_returns_422(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        response = client.post(
            f"/interviews/sessions/{session_id}/answers",
            json=answer_payload(current, text=""),
        )
        assert response.status_code == 422
        assert response.json()["error"] == "INVALID_ANSWER"

    def test_missing_evidence_reference_returns_422(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        assert current["question"]["evidence_citations"]
        response = client.post(
            f"/interviews/sessions/{session_id}/answers",
            json=answer_payload(current, refs=[]),
        )
        assert response.status_code == 422
        assert response.json()["error"] == "MISSING_EVIDENCE_REFERENCE"

    def test_duplicate_answer_returns_422(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        submit_answer(session_id, answer_payload(current))
        response = client.post(
            f"/interviews/sessions/{session_id}/answers",
            json=answer_payload(current),
        )
        assert response.status_code == 422
        assert response.json()["error"] == "INVALID_ANSWER"

    def test_answer_without_active_question_returns_409(self) -> None:
        session_id = create_session()["session_id"]
        current = active_question(session_id)
        assert client.post(f"/interviews/sessions/{session_id}/pause").status_code == 200
        response = client.post(
            f"/interviews/sessions/{session_id}/answers",
            json=answer_payload(current),
        )
        assert response.status_code == 409
        assert response.json()["error"] == "NO_ACTIVE_QUESTION"

    def test_malformed_answer_request_returns_422(self) -> None:
        session_id = create_session()["session_id"]
        response = client.post(
            f"/interviews/sessions/{session_id}/answers",
            json={"question_id": "q1"},
        )
        assert response.status_code == 422


class TestAdvanceFlow:

    def test_advances_question_by_question_and_completes(self) -> None:
        session_id = create_session()["session_id"]
        question_count = client.get(f"/interviews/sessions/{session_id}").json()["question_count"]
        assert question_count >= 1
        first = active_question(session_id)
        submit_answer(session_id, answer_payload(first))
        advance = client.post(f"/interviews/sessions/{session_id}/next")
        assert advance.status_code == 200
        body = advance.json()
        if question_count == 1:
            assert body["completed"] is True
            return
        assert body["completed"] is False
        assert body["session"]["answered_count"] == 1
        assert body["session"]["current_question_index"] == 1
        assert body["next_question"]["index"] == 2
        assert body["report"] is None

    def test_completion_returns_report(self) -> None:
        session_id = create_session()["session_id"]
        completed_body: dict | None = None
        for _ in range(50):
            session = client.get(f"/interviews/sessions/{session_id}").json()
            if session["state"] == "completed":
                break
            current = session["current_question"]
            assert current is not None
            submit_answer(session_id, answer_payload(current))
            completed_body = client.post(f"/interviews/sessions/{session_id}/next").json()
            if completed_body["completed"]:
                break
        assert completed_body is not None
        assert completed_body["completed"] is True
        assert completed_body["next_question"] is None
        report = completed_body["report"]
        assert report["session_id"] == session_id
        assert report["summary"]["question_count"] == completed_body["session"]["question_count"]
        assert report["summary"]["answered_questions"] == report["summary"]["question_count"]
        assert report["summary"]["average_score"] >= 0
        assert isinstance(report["summary"]["feedback"], list)

    def test_next_when_paused_returns_409(self) -> None:
        session_id = create_session()["session_id"]
        assert client.post(f"/interviews/sessions/{session_id}/pause").status_code == 200
        response = client.post(f"/interviews/sessions/{session_id}/next")
        assert response.status_code == 409
        assert response.json()["error"] == "INVALID_SESSION_STATE"


class TestPauseResume:

    def test_pause_and_resume_preserve_state(self) -> None:
        session_id = create_session()["session_id"]
        paused = client.post(f"/interviews/sessions/{session_id}/pause")
        assert paused.status_code == 200
        assert paused.json()["state"] == "paused"
        session = client.get(f"/interviews/sessions/{session_id}").json()
        assert session["state"] == "paused"
        assert session["current_question"] is None
        assert session["current_question_index"] == 0
        resumed = client.post(f"/interviews/sessions/{session_id}/resume")
        assert resumed.status_code == 200
        assert resumed.json()["state"] == "in_progress"
        assert resumed.json()["current_question"] is not None

    def test_pause_when_not_in_progress_returns_409(self) -> None:
        session_id = create_session()["session_id"]
        assert client.post(f"/interviews/sessions/{session_id}/pause").status_code == 200
        response = client.post(f"/interviews/sessions/{session_id}/pause")
        assert response.status_code == 409
        assert response.json()["error"] == "INVALID_SESSION_STATE"

    def test_resume_when_not_paused_returns_409(self) -> None:
        session_id = create_session()["session_id"]
        response = client.post(f"/interviews/sessions/{session_id}/resume")
        assert response.status_code == 409
        assert response.json()["error"] == "INVALID_SESSION_STATE"


class TestRetrieveSession:

    def test_get_session_returns_state_and_metadata(self) -> None:
        session_id = create_session()["session_id"]
        response = client.get(f"/interviews/sessions/{session_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == session_id
        assert body["state"] == "in_progress"
        assert body["question_count"] > 0
        assert isinstance(body["answers"], list)
        assert body["current_question"] is not None

    def test_get_unknown_session_returns_404(self) -> None:
        response = client.get("/interviews/sessions/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"] == "NOT_FOUND"

    def test_unknown_session_actions_return_404(self) -> None:
        actions = [
            ("post", "/interviews/sessions/does-not-exist/answers",
             {"question_id": "q1", "text": "answer", "evidence_references": []}),
            ("post", "/interviews/sessions/does-not-exist/next", None),
            ("post", "/interviews/sessions/does-not-exist/pause", None),
            ("post", "/interviews/sessions/does-not-exist/resume", None),
            ("get", "/interviews/sessions/does-not-exist/report", None),
        ]
        for method, url, payload in actions:
            response = getattr(client, method)(url, json=payload) if payload is not None else getattr(client, method)(url)
            assert response.status_code == 404, f"{method} {url} -> {response.status_code}"


class TestReport:

    def test_report_requires_completed_session(self) -> None:
        session_id = create_session()["session_id"]
        response = client.get(f"/interviews/sessions/{session_id}/report")
        assert response.status_code == 409
        assert response.json()["error"] == "SESSION_NOT_COMPLETED"

    def test_report_after_completion(self) -> None:
        session_id = create_session()["session_id"]
        complete_session(session_id)
        response = client.get(f"/interviews/sessions/{session_id}/report")
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == session_id
        summary = body["summary"]
        assert summary["question_count"] == summary["answered_questions"] > 0
        assert summary["average_score"] >= 0
        assert isinstance(summary["feedback"], list)
        assert summary["feedback"]
