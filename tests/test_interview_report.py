"""M1.18 refactor — interview report builder tests.

Covers the module-level ``build_report`` and ``attach_summary`` functions that
were moved out of the API layer into the Interview Simulation module so the
API stays a thin transport. Behavior is identical to the previously
API-internal implementation: deterministic and immutable.
"""

from __future__ import annotations

from careeros import (
    AnswerEvaluation,
    EvidenceCitation,
    EvaluationSummary,
    InterviewAnswer,
    InterviewPlan,
    InterviewQuestion,
    InterviewSession,
    QuestionType,
    SessionEngine,
    SessionState,
    attach_summary,
    build_report,
)
from careeros.interview.simulation.report import build_report as module_build_report


_QUESTION = InterviewQuestion(
    id="q1",
    category=QuestionType.BEHAVIORAL,
    text="Describe how you led a project that improved reliability.",
    competency_ids=("reliability-engineering",),
    context_refs=({"id": "exp-1", "type": "experience"},),
    evidence_citations=(
        EvidenceCitation(
            element_type="experience",
            element_id="exp-1",
            quote="Reduced deployment time by 60%",
        ),
    ),
)

_STRONG_ANSWER = (
    "As a platform engineer I owned the reliability work. I led the migration, "
    "which reduced deployment time by 60% as a result."
)


def _answer() -> InterviewAnswer:
    return InterviewAnswer(
        id="s-1:q1:answer",
        session_id="s-1",
        question_id="s-1:q1",
        text=_STRONG_ANSWER,
        evaluation=AnswerEvaluation(
            covers_claim=True,
            has_metric=True,
            cites_evidence=True,
            follows_structure=True,
            matches_question_competencies=True,
        ),
    )


def _completed_session() -> InterviewSession:
    plan = InterviewPlan(
        profile_version="v1",
        person_id="person-1",
        target_role="Platform Engineer",
        questions=(_QUESTION,),
    )
    engine = SessionEngine()
    session = engine.start_session(engine.create_session(plan, "s-1"))
    session = engine.submit_answer(session, _answer())
    return engine.complete_session(session)


def _weak_evaluation_summary() -> EvaluationSummary:
    return EvaluationSummary(
        total_answers=1,
        coverage=0,
        evidence=0,
        claim_alignment=0,
        measurability=0,
        structure=0,
        inconsistent_answers=1,
    )


class TestAttachSummary:

    def test_populates_summary_field(self) -> None:
        session = _completed_session()
        summary = SessionEngine().build_summary(session)
        attached = attach_summary(session, summary)
        assert attached.summary is summary
        assert attached.summary == summary
        assert attached.state == session.state
        assert attached.answers == session.answers

    def test_original_session_is_not_mutated(self) -> None:
        session = _completed_session()
        summary = SessionEngine().build_summary(session)
        attach_summary(session, summary)
        assert session.summary is None


class TestBuildReport:

    def test_strong_session_yields_only_strengths(self) -> None:
        session = _completed_session()
        report = build_report(session, EvaluationSummary(
            total_answers=1,
            coverage=1,
            evidence=1,
            claim_alignment=1,
            measurability=1,
            structure=1,
            inconsistent_answers=0,
        ))
        assert report.id == "s-1:report"
        assert report.session_id == "s-1"
        assert report.profile_id == "person-1"
        assert report.plan_ref == "person-1:v1:Platform Engineer"
        assert len(report.strengths) == 5
        assert report.weaknesses == ()
        assert report.recommendations == ()
        assert report.answers[0] == _answer()

    def test_weak_session_yields_weaknesses_and_recommendations(self) -> None:
        session = _completed_session()
        report = build_report(session, _weak_evaluation_summary())
        assert report.strengths == ()
        assert len(report.weaknesses) == 6
        assert len(report.recommendations) == 3
        assert any("Measurability" in w for w in report.weaknesses)
        assert any("Structure" in w for w in report.weaknesses)

    def test_report_uses_attached_summary_when_present(self) -> None:
        session = attach_summary(
            _completed_session(),
            SessionEngine().build_summary(_completed_session()),
        )
        report = build_report(session, _weak_evaluation_summary())
        assert report.summary is session.summary

    def test_deterministic(self) -> None:
        session = _completed_session()
        evaluation = _weak_evaluation_summary()
        first = build_report(session, evaluation).to_dict()
        second = build_report(session, evaluation).to_dict()
        assert first == second

    def test_exported_from_simulation_package(self) -> None:
        assert module_build_report is build_report


class TestCompletedSessionState:

    def test_completed_session_builds_summary(self) -> None:
        session = _completed_session()
        assert session.state == SessionState.COMPLETED
        summary = SessionEngine().build_summary(session)
        assert summary.answered_questions == 1
