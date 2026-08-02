"""M1.17.3 — Interview Simulation session engine tests.

Covers the public engine contract from
``docs/platform-beta/interview-simulation/07-session-engine-design.md``:
create/start/next_question/submit_answer/pause/resume/complete/build_summary,
state transition enforcement, answer validation, metrics, summary building,
immutability, determinism, and facade exports.
"""

from __future__ import annotations

import pytest

from careeros import (
    AnswerEvaluation,
    EvidenceCitation,
    InterviewAnswer,
    InterviewPlan,
    InterviewQuestion,
    InterviewQuestionInstance,
    InterviewSession,
    InterviewSessionError,
    InvalidAnswerError,
    InvalidPlanError,
    InvalidSessionStateError,
    NoActiveQuestionError,
    QuestionType,
    SessionEngine,
    SessionMetrics,
    SessionState,
    SuggestedAnswer,
)


def _question(question_id: str, category: QuestionType = QuestionType.TECHNICAL) -> InterviewQuestion:
    return InterviewQuestion(
        id=question_id,
        category=category,
        text=f"Question {question_id}?",
        competency_ids=(f"comp-{question_id}",),
        context_refs=({"id": f"exp-{question_id}", "type": "experience"},),
        evidence_citations=(
            EvidenceCitation(element_type="skill", element_id=f"skill-{question_id}", quote="Python"),
        ),
        difficulty="intermediate",
    )


def _plan(*question_ids: str) -> InterviewPlan:
    return InterviewPlan(
        profile_version="v1",
        person_id="person-1",
        target_role="Platform Engineer",
        questions=tuple(_question(qid) for qid in question_ids),
    )


def _answer(session: InterviewSession, question: InterviewQuestionInstance, text: str = "My answer") -> InterviewAnswer:
    return InterviewAnswer(
        id=f"{session.id}:{question.id}:answer",
        session_id=session.id,
        question_id=question.id,
        text=text,
        duration_seconds=60,
    )


@pytest.fixture
def engine() -> SessionEngine:
    return SessionEngine()


@pytest.fixture
def started_session(engine: SessionEngine) -> InterviewSession:
    return engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))


# --------------------------------------------------------------------------
# create_session
# --------------------------------------------------------------------------


class TestCreateSession:

    def test_creates_draft_session(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1", "q2"), "s-1")
        assert session.id == "s-1"
        assert session.state == SessionState.DRAFT
        assert session.profile_id == "person-1"
        assert session.question_count == 2

    def test_plan_ref_is_deterministic(self, engine: SessionEngine) -> None:
        ref1 = engine.create_session(_plan("q1"), "s-1").plan_ref
        ref2 = engine.create_session(_plan("q1"), "s-2").plan_ref
        assert ref1 == ref2
        assert ref1 == "person-1:v1:Platform Engineer"

    def test_questions_materialized_in_order(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1", "q2", "q3"), "s-1")
        assert [q.order for q in session.questions] == [0, 1, 2]
        assert [q.id for q in session.questions] == ["s-1:q1", "s-1:q2", "s-1:q3"]
        assert all(q.session_id == "s-1" for q in session.questions)

    def test_question_fields_mapped_from_plan(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        q = session.questions[0]
        assert q.question_text == "Question q1?"
        assert q.category == "technical"
        assert q.difficulty == "intermediate"
        assert q.competency_ids == ("comp-q1",)
        assert q.context_refs == ({"id": "exp-q1", "type": "experience"},)
        assert q.evidence_citations[0].element_id == "skill-q1"
        assert q.time_limit_seconds is None

    def test_metadata_attached(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1", metadata={"focus": "technical"})
        assert session.metadata == {"focus": "technical"}

    def test_empty_plan_creates_empty_session(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan(), "s-1")
        assert session.question_count == 0
        assert session.answer_count == 0

    def test_invalid_plan_raises(self, engine: SessionEngine) -> None:
        with pytest.raises(InvalidPlanError):
            engine.create_session({"not": "a plan"}, "s-1")

    def test_plan_without_person_raises(self, engine: SessionEngine) -> None:
        plan = InterviewPlan(profile_version="v1", person_id="")
        with pytest.raises(InvalidPlanError):
            engine.create_session(plan, "s-1")


# --------------------------------------------------------------------------
# start_session
# --------------------------------------------------------------------------


class TestStartSession:

    def test_start_draft(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        started = engine.start_session(session)
        assert started.state == SessionState.IN_PROGRESS
        assert session.state == SessionState.DRAFT

    def test_start_ready(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        ready = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=SessionState.READY, questions=session.questions,
        )
        assert engine.start_session(ready).state == SessionState.IN_PROGRESS

    @pytest.mark.parametrize("state", [
        SessionState.PAUSED,
        SessionState.COMPLETED,
        SessionState.REVIEWED,
        SessionState.ARCHIVED,
    ])
    def test_start_invalid_state_raises(self, engine: SessionEngine, state: SessionState) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        session = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=state, questions=session.questions,
        )
        with pytest.raises(InvalidSessionStateError):
            engine.start_session(session)


# --------------------------------------------------------------------------
# next_question
# --------------------------------------------------------------------------


class TestNextQuestion:

    def test_returns_first_question(self, started_session: InterviewSession) -> None:
        q = SessionEngine().next_question(started_session)
        assert q.id == "s-1:q1"

    def test_advances_after_answers(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q1 = engine.next_question(started_session)
        answered = engine.submit_answer(started_session, _answer(started_session, q1))
        q2 = engine.next_question(answered)
        assert q2.id == "s-1:q2"

    def test_exhausted_raises(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        session = engine.start_session(session)
        q = engine.next_question(session)
        session = engine.submit_answer(session, _answer(session, q))
        with pytest.raises(NoActiveQuestionError):
            engine.next_question(session)

    def test_not_in_progress_raises(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        with pytest.raises(InvalidSessionStateError):
            engine.next_question(session)

    def test_is_deterministic(self, engine: SessionEngine) -> None:
        s1 = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
        s2 = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
        assert engine.next_question(s1).to_dict() == engine.next_question(s2).to_dict()


# --------------------------------------------------------------------------
# submit_answer
# --------------------------------------------------------------------------


class TestSubmitAnswer:

    def test_records_answer(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q = engine.next_question(started_session)
        updated = engine.submit_answer(started_session, _answer(started_session, q))
        assert updated.answer_count == 1
        assert updated.answers[0].text == "My answer"
        assert updated.state == SessionState.IN_PROGRESS
        assert started_session.answer_count == 0

    def test_updates_metrics(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q = engine.next_question(started_session)
        updated = engine.submit_answer(started_session, _answer(started_session, q, "A"))
        assert updated.metrics is not None
        assert updated.metrics.total_questions == 2
        assert updated.metrics.answered_questions == 1
        assert updated.metrics.total_duration_seconds == 60
        assert updated.metrics.average_duration_seconds == 60.0

    def test_empty_text_raises(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q = engine.next_question(started_session)
        with pytest.raises(InvalidAnswerError):
            engine.submit_answer(started_session, _answer(started_session, q, "  "))

    def test_wrong_session_raises(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q = engine.next_question(started_session)
        bad = _answer(started_session, q)
        bad = InterviewAnswer(id=bad.id, session_id="other", question_id=bad.question_id, text=bad.text)
        with pytest.raises(InvalidAnswerError):
            engine.submit_answer(started_session, bad)

    def test_wrong_question_raises(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
        q2 = session.questions[1]
        with pytest.raises(InvalidAnswerError):
            engine.submit_answer(session, _answer(session, q2))

    def test_no_active_question_raises(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1"), "s-1"))
        q = engine.next_question(session)
        session = engine.submit_answer(session, _answer(session, q))
        with pytest.raises(InvalidAnswerError):
            engine.submit_answer(session, _answer(session, q, "again"))

    def test_not_in_progress_raises(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        q = session.questions[0]
        with pytest.raises(InvalidSessionStateError):
            engine.submit_answer(session, _answer(session, q))


# --------------------------------------------------------------------------
# pause / resume
# --------------------------------------------------------------------------


class TestPauseResume:

    def test_pause_in_progress(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        paused = engine.pause_session(started_session)
        assert paused.state == SessionState.PAUSED
        assert started_session.state == SessionState.IN_PROGRESS

    def test_resume_paused(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1"), "s-1"))
        session = engine.pause_session(session)
        resumed = engine.resume_session(session)
        assert resumed.state == SessionState.IN_PROGRESS

    def test_pause_not_in_progress_raises(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        with pytest.raises(InvalidSessionStateError):
            engine.pause_session(session)

    def test_resume_non_paused_raises(self, started_session: InterviewSession) -> None:
        with pytest.raises(InvalidSessionStateError):
            SessionEngine().resume_session(started_session)


# --------------------------------------------------------------------------
# complete_session
# --------------------------------------------------------------------------


class TestCompleteSession:

    def test_complete_in_progress(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        completed = engine.complete_session(started_session)
        assert completed.state == SessionState.COMPLETED

    def test_complete_paused(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1"), "s-1"))
        session = engine.pause_session(session)
        assert engine.complete_session(session).state == SessionState.COMPLETED

    def test_complete_ready_fast_path(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        ready = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=SessionState.READY, questions=session.questions,
        )
        completed = engine.complete_session(ready)
        assert completed.state == SessionState.COMPLETED
        assert completed.answer_count == 0

    def test_complete_finalizes_metrics(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        q = engine.next_question(started_session)
        session = engine.submit_answer(started_session, _answer(started_session, q))
        completed = engine.complete_session(session)
        assert completed.metrics is not None
        assert completed.metrics.answered_questions == 1

    @pytest.mark.parametrize("state", [
        SessionState.DRAFT,
        SessionState.COMPLETED,
        SessionState.REVIEWED,
        SessionState.ARCHIVED,
    ])
    def test_complete_invalid_state_raises(self, engine: SessionEngine, state: SessionState) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        session = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=state, questions=session.questions,
        )
        with pytest.raises(InvalidSessionStateError):
            engine.complete_session(session)


# --------------------------------------------------------------------------
# build_summary
# --------------------------------------------------------------------------


class TestBuildSummary:

    def test_requires_completed(self, started_session: InterviewSession) -> None:
        with pytest.raises(InvalidSessionStateError):
            SessionEngine().build_summary(started_session)

    def test_builds_counts_from_evaluations(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
        q1 = engine.next_question(session)
        a1 = _answer(session, q1)
        a1 = InterviewAnswer(
            id=a1.id, session_id=a1.session_id, question_id=a1.question_id, text=a1.text,
            evaluation=AnswerEvaluation(covers_claim=True, has_metric=True, cites_evidence=True),
        )
        session = engine.submit_answer(session, a1)
        q2 = engine.next_question(session)
        a2 = _answer(session, q2, "vague")
        a2 = InterviewAnswer(
            id=a2.id, session_id=a2.session_id, question_id=a2.question_id, text=a2.text,
            evaluation=AnswerEvaluation(covers_claim=False),
        )
        session = engine.submit_answer(session, a2)
        session = engine.complete_session(session)
        summary = engine.build_summary(session)
        assert summary.total_questions == 2
        assert summary.answered_questions == 2
        assert summary.covered_claims == 1
        assert summary.metric_citations == 1
        assert summary.evidence_citations == 1
        assert summary.structured_answers == 0
        assert summary.strong_answers == 1
        assert summary.weak_answers == 1

    def test_fast_path_summary(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1", "q2"), "s-1")
        ready = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=SessionState.READY, questions=session.questions,
        )
        completed = engine.complete_session(ready)
        summary = engine.build_summary(completed)
        assert summary.total_questions == 2
        assert summary.answered_questions == 0
        assert summary.covered_claims == 0


# --------------------------------------------------------------------------
# Determinism & immutability
# --------------------------------------------------------------------------


class TestDeterminismAndImmutability:

    def test_full_flow_is_deterministic(self) -> None:
        engine = SessionEngine()

        def run() -> dict:
            session = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
            q1 = engine.next_question(session)
            session = engine.submit_answer(session, _answer(session, q1))
            q2 = engine.next_question(session)
            session = engine.submit_answer(session, _answer(session, q2))
            session = engine.complete_session(session)
            return session.to_dict()

        assert run() == run()

    def test_operations_do_not_mutate_input(self, started_session: InterviewSession) -> None:
        engine = SessionEngine()
        original = started_session.to_dict()
        q = engine.next_question(started_session)
        engine.submit_answer(started_session, _answer(started_session, q))
        engine.pause_session(started_session)
        engine.complete_session(started_session)
        assert started_session.to_dict() == original

    def test_paused_session_preserves_progress(self, engine: SessionEngine) -> None:
        session = engine.start_session(engine.create_session(_plan("q1", "q2"), "s-1"))
        q1 = engine.next_question(session)
        session = engine.submit_answer(session, _answer(session, q1))
        session = engine.pause_session(session)
        resumed = engine.resume_session(session)
        q2 = engine.next_question(resumed)
        assert q2.id == "s-1:q2"
        assert resumed.answer_count == 1


# --------------------------------------------------------------------------
# Facade exports
# --------------------------------------------------------------------------


class TestFacadeExports:

    def test_session_engine_accessible_from_careeros(self) -> None:
        assert SessionEngine is not None

    def test_engine_is_exported_from_interview(self) -> None:
        from careeros.interview import SessionEngine as InterviewSessionEngine
        assert InterviewSessionEngine is SessionEngine

    def test_new_exceptions_exported(self) -> None:
        assert issubclass(InvalidPlanError, InterviewSessionError)
        assert issubclass(NoActiveQuestionError, InterviewSessionError)
        from careeros.interview.simulation import InvalidPlanError as IPE, NoActiveQuestionError as NAQE
        assert IPE is InvalidPlanError
        assert NAQE is NoActiveQuestionError

    def test_engine_preserves_knowledge_separation(self, engine: SessionEngine) -> None:
        session = engine.create_session(_plan("q1"), "s-1")
        assert session.profile_id == "person-1"
        q = session.questions[0]
        assert q.evidence_citations[0].source_ref() == {"id": "skill-q1", "type": "skill"}
        assert "Python" in q.to_dict()["evidence_citations"][0]["quote"]
        assert "person-1" not in session.to_dict()["questions"][0]["question_text"]
