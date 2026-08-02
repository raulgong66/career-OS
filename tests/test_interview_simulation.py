"""M1.17.2 — Interview Simulation domain model tests.

Covers object construction, immutability, serialization, validation,
evidence references, enum values, report generation models, empty
session, completed session, and facade exports.
"""

from __future__ import annotations

import json

import pytest

from careeros import (
    AnswerEvaluation,
    EvidenceCitation,
    InterviewAnswer,
    InterviewFeedback,
    InterviewQuestionInstance,
    InterviewReport,
    InterviewSession,
    InterviewSessionError,
    InterviewSummary,
    InvalidAnswerError,
    InvalidSessionStateError,
    SessionMetrics,
    SessionState,
    SuggestedAnswer,
)


# --------------------------------------------------------------------------
# SessionState
# --------------------------------------------------------------------------


class TestSessionState:

    def test_has_all_states(self) -> None:
        expected = {
            "draft", "ready", "in_progress", "paused",
            "completed", "reviewed", "archived",
        }
        assert {s.value for s in SessionState} == expected

    def test_draft_is_default(self) -> None:
        session = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        assert session.state == SessionState.DRAFT

    def test_enum_values_are_strings(self) -> None:
        assert SessionState.DRAFT.value == "draft"
        assert SessionState.COMPLETED.value == "completed"

    def test_enum_from_value(self) -> None:
        assert SessionState("in_progress") == SessionState.IN_PROGRESS
        assert SessionState("archived") == SessionState.ARCHIVED

    def test_invalid_state_value_raises(self) -> None:
        with pytest.raises(ValueError):
            SessionState("nonexistent")  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# InterviewSession — construction
# --------------------------------------------------------------------------


class TestInterviewSessionConstruction:

    def test_minimal_session(self) -> None:
        session = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        assert session.id == "s-1"
        assert session.plan_ref == "plan-1"
        assert session.profile_id == "p-1"
        assert session.state == SessionState.DRAFT
        assert session.questions == ()
        assert session.answers == ()
        assert session.question_count == 0
        assert session.answer_count == 0
        assert session.started_at is None
        assert session.completed_at is None
        assert session.paused_at is None
        assert session.metrics is None
        assert session.summary is None

    def test_session_with_questions_and_answers(self) -> None:
        answer = InterviewAnswer(
            id="a-1", session_id="s-1", question_id="q-1", text="My answer"
        )
        question = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Tell me about Kubernetes.",
            category="technical",
        )
        session = InterviewSession(
            id="s-1",
            plan_ref="plan-1",
            profile_id="p-1",
            state=SessionState.IN_PROGRESS,
            questions=(question,),
            answers=(answer,),
            started_at="2026-01-01T10:00:00Z",
        )
        assert session.question_count == 1
        assert session.answer_count == 1
        assert session.started_at == "2026-01-01T10:00:00Z"

    def test_session_is_immutable(self) -> None:
        session = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        with pytest.raises(AttributeError):
            session.state = SessionState.IN_PROGRESS  # type: ignore[misc]

    def test_questions_and_answers_ordered(self) -> None:
        q1 = InterviewQuestionInstance(
            id="q-1", session_id="s-1", question_text="Q1", category="technical", order=1
        )
        q2 = InterviewQuestionInstance(
            id="q-2", session_id="s-1", question_text="Q2", category="behavioral", order=2
        )
        session = InterviewSession(
            id="s-1", plan_ref="plan-1", profile_id="p-1", questions=(q2, q1)
        )
        # Preserved insertion order
        assert session.questions[0].id == "q-2"
        assert session.questions[1].id == "q-1"


# --------------------------------------------------------------------------
# InterviewQuestionInstance
# --------------------------------------------------------------------------


class TestInterviewQuestionInstance:

    def test_minimal_question_instance(self) -> None:
        q = InterviewQuestionInstance(
            id="q-1", session_id="s-1", question_text="Tell me about X.", category="behavioral"
        )
        assert q.id == "q-1"
        assert q.difficulty == "intermediate"
        assert q.competency_ids == ()
        assert q.context_refs == ()
        assert q.evidence_citations == ()
        assert q.suggested_answer is None
        assert q.order == 0
        assert q.time_limit_seconds is None

    def test_question_with_evidence_citations(self) -> None:
        citations = (
            EvidenceCitation(element_type="skill", element_id="skill-k8s", quote="Kubernetes"),
            EvidenceCitation(element_type="experience", element_id="exp-acme", quote="Led migration"),
        )
        q = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Tell me about Kubernetes.",
            category="technical",
            difficulty="advanced",
            competency_ids=("competency-skill-k8s",),
            evidence_citations=citations,
            order=1,
            time_limit_seconds=120,
        )
        assert len(q.evidence_citations) == 2
        assert q.evidence_citations[0].source_ref() == {"id": "skill-k8s", "type": "skill"}
        assert q.difficulty == "advanced"
        assert q.order == 1
        assert q.time_limit_seconds == 120

    def test_question_with_suggested_answer(self) -> None:
        answer = SuggestedAnswer(
            situation="Platform Engineer at ACME",
            action="Led migration of 200 services to Kubernetes",
        )
        q = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Tell me about Kubernetes.",
            category="technical",
            suggested_answer=answer,
        )
        assert q.suggested_answer is not None
        assert q.suggested_answer.situation == "Platform Engineer at ACME"


# --------------------------------------------------------------------------
# InterviewAnswer
# --------------------------------------------------------------------------


class TestInterviewAnswer:

    def test_minimal_answer(self) -> None:
        a = InterviewAnswer(id="a-1", session_id="s-1", question_id="q-1", text="My answer")
        assert a.text == "My answer"
        assert a.answered_at is None
        assert a.duration_seconds is None
        assert a.evaluation is None
        assert a.feedback is None

    def test_answer_is_immutable(self) -> None:
        a = InterviewAnswer(id="a-1", session_id="s-1", question_id="q-1", text="Text")
        with pytest.raises(AttributeError):
            a.text = "changed"  # type: ignore[misc]

    def test_answer_with_evaluation_and_feedback(self) -> None:
        evaluation = AnswerEvaluation(covers_claim=True, has_metric=True)
        feedback = InterviewFeedback(
            id="f-1",
            question_id="q-1",
            answer_id="a-1",
            missing=("evidence", "structure"),
            improvement_recommendation="Include specific metrics",
        )
        a = InterviewAnswer(
            id="a-1",
            session_id="s-1",
            question_id="q-1",
            text="I reduced costs by 40% through K8s migration.",
            answered_at="2026-01-01T10:05:00Z",
            duration_seconds=300,
            evaluation=evaluation,
            feedback=feedback,
        )
        assert a.answered_at == "2026-01-01T10:05:00Z"
        assert a.duration_seconds == 300
        assert a.evaluation is not None
        assert a.evaluation.covers_claim is True
        assert a.feedback is not None
        assert "evidence" in a.feedback.missing


# --------------------------------------------------------------------------
# AnswerEvaluation
# --------------------------------------------------------------------------


class TestAnswerEvaluation:

    def test_default_evaluation(self) -> None:
        e = AnswerEvaluation()
        assert e.covers_claim is False
        assert e.has_metric is False
        assert e.cites_evidence is False
        assert e.follows_structure is False
        assert e.matches_question_competencies is False
        assert e.citations == ()

    def test_evaluation_with_citations(self) -> None:
        citations = (EvidenceCitation(element_type="skill", element_id="skill-k8s"),)
        e = AnswerEvaluation(
            covers_claim=True,
            has_metric=True,
            cites_evidence=True,
            citations=citations,
        )
        assert e.covers_claim is True
        assert len(e.citations) == 1


# --------------------------------------------------------------------------
# InterviewFeedback
# --------------------------------------------------------------------------


class TestInterviewFeedback:

    def test_minimal_feedback(self) -> None:
        f = InterviewFeedback(id="f-1", question_id="q-1", answer_id="a-1")
        assert f.missing == ()
        assert f.improvement_recommendation is None
        assert f.citations == ()

    def test_feedback_with_all_fields(self) -> None:
        f = InterviewFeedback(
            id="f-1",
            question_id="q-1",
            answer_id="a-1",
            missing=("metric", "evidence"),
            improvement_recommendation="Add numbers and cite experience evidence.",
            citations=(EvidenceCitation(element_type="experience", element_id="exp-acme"),),
        )
        assert "metric" in f.missing
        assert f.improvement_recommendation is not None
        assert len(f.citations) == 1


# --------------------------------------------------------------------------
# SessionMetrics
# --------------------------------------------------------------------------


class TestSessionMetrics:

    def test_default_metrics(self) -> None:
        m = SessionMetrics()
        assert m.total_questions == 0
        assert m.answered_questions == 0
        assert m.average_duration_seconds is None
        assert m.total_duration_seconds is None

    def test_metrics_with_values(self) -> None:
        m = SessionMetrics(
            total_questions=10,
            answered_questions=8,
            average_duration_seconds=180,
            total_duration_seconds=1440,
        )
        assert m.total_questions == 10
        assert m.average_duration_seconds == 180


# --------------------------------------------------------------------------
# InterviewSummary
# --------------------------------------------------------------------------


class TestInterviewSummary:

    def test_default_summary(self) -> None:
        s = InterviewSummary()
        assert s.total_questions == 0
        assert s.strong_answers == 0
        assert s.weak_answers == 0

    def test_summary_with_values(self) -> None:
        s = InterviewSummary(
            total_questions=10,
            answered_questions=8,
            covered_claims=5,
            metric_citations=4,
            evidence_citations=6,
            structured_answers=7,
            strong_answers=4,
            weak_answers=1,
        )
        assert s.strong_answers == 4
        assert s.weak_answers == 1


# --------------------------------------------------------------------------
# InterviewReport
# --------------------------------------------------------------------------


class TestInterviewReport:

    def test_minimal_report(self) -> None:
        summary = InterviewSummary()
        metrics = SessionMetrics()
        report = InterviewReport(
            id="r-1",
            session_id="s-1",
            profile_id="p-1",
            plan_ref="plan-1",
            summary=summary,
            session_metrics=metrics,
        )
        assert report.id == "r-1"
        assert report.answers == ()
        assert report.strengths == ()
        assert report.weaknesses == ()
        assert report.recommendations == ()

    def test_report_with_answers_and_strengths(self) -> None:
        answer = InterviewAnswer(
            id="a-1", session_id="s-1", question_id="q-1", text="Answer"
        )
        report = InterviewReport(
            id="r-1",
            session_id="s-1",
            profile_id="p-1",
            plan_ref="plan-1",
            summary=InterviewSummary(strong_answers=1),
            session_metrics=SessionMetrics(answered_questions=1),
            answers=(answer,),
            strengths=("Strong STAR structure", "Uses metrics"),
            weaknesses=("Needs more evidence citations",),
            recommendations=("Practice citing experience evidence",),
        )
        assert len(report.answers) == 1
        assert "Strong STAR structure" in report.strengths
        assert "Needs more evidence citations" in report.weaknesses
        assert len(report.recommendations) == 1


# --------------------------------------------------------------------------
# Evidence separation (knowledge / runtime)
# --------------------------------------------------------------------------


class TestEvidenceSeparation:

    def test_runtime_objects_use_evidence_citations_not_profile_data(self) -> None:
        """Runtime objects reference canonical knowledge, never own it."""
        citation = EvidenceCitation(
            element_type="skill", element_id="skill-k8s", quote="Kubernetes"
        )
        q = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Tell me about K8s.",
            category="technical",
            evidence_citations=(citation,),
        )
        assert q.evidence_citations[0].source_ref() == {"id": "skill-k8s", "type": "skill"}
        assert q.evidence_citations[0].quote == "Kubernetes"

    def test_answer_citations_are_evidence_references(self) -> None:
        citation = EvidenceCitation(
            element_type="experience", element_id="exp-acme", quote="Led migration"
        )
        evaluation = AnswerEvaluation(citations=(citation,))
        assert evaluation.citations[0].element_type == "experience"
        assert evaluation.citations[0].element_id == "exp-acme"

    def test_feedback_citations_are_evidence_references(self) -> None:
        citation = EvidenceCitation(
            element_type="achievement", element_id="achievement-cost-reduction"
        )
        feedback = InterviewFeedback(
            id="f-1", question_id="q-1", answer_id="a-1", citations=(citation,)
        )
        assert feedback.citations[0].element_type == "achievement"
        assert feedback.citations[0].element_id == "achievement-cost-reduction"


# --------------------------------------------------------------------------
# Serialization (to_dict / to_json)
# --------------------------------------------------------------------------


class TestSerialization:

    def test_session_to_dict(self) -> None:
        session = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        d = session.to_dict()
        assert d["id"] == "s-1"
        assert d["state"] == "draft"
        assert d["questions"] == []
        assert d["answers"] == []
        assert "metrics" not in d or d["metrics"] is None
        assert "summary" not in d or d["summary"] is None

    def test_session_to_json(self) -> None:
        session = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        j = session.to_json()
        parsed = json.loads(j)
        assert parsed["id"] == "s-1"
        assert parsed["state"] == "draft"

    def test_session_with_data_to_dict(self) -> None:
        answer = InterviewAnswer(
            id="a-1", session_id="s-1", question_id="q-1", text="My answer"
        )
        question = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Q?",
            category="technical",
            difficulty="advanced",
            competency_ids=("comp-1",),
            context_refs=({"id": "exp-1", "type": "experience"},),
            evidence_citations=(
                EvidenceCitation(element_type="skill", element_id="skill-1", quote="Python"),
            ),
            order=1,
        )
        session = InterviewSession(
            id="s-1",
            plan_ref="plan-1",
            profile_id="p-1",
            state=SessionState.IN_PROGRESS,
            questions=(question,),
            answers=(answer,),
            metrics=SessionMetrics(total_questions=1, answered_questions=1),
        )
        d = session.to_dict()
        assert d["state"] == "in_progress"
        assert len(d["questions"]) == 1
        assert d["questions"][0]["question_text"] == "Q?"
        assert d["questions"][0]["difficulty"] == "advanced"
        assert d["questions"][0]["competency_ids"] == ["comp-1"]
        assert d["questions"][0]["context_refs"] == [{"id": "exp-1", "type": "experience"}]
        assert d["questions"][0]["order"] == 1
        assert len(d["answers"]) == 1
        assert d["answers"][0]["text"] == "My answer"
        assert d["metrics"] is not None
        assert d["metrics"]["total_questions"] == 1

    def test_answer_to_dict(self) -> None:
        evaluation = AnswerEvaluation(covers_claim=True, has_metric=True)
        a = InterviewAnswer(
            id="a-1",
            session_id="s-1",
            question_id="q-1",
            text="My answer",
            answered_at="2026-01-01T10:00:00Z",
            duration_seconds=120,
            evaluation=evaluation,
        )
        d = a.to_dict()
        assert d["id"] == "a-1"
        assert d["duration_seconds"] == 120
        assert d["evaluation"]["covers_claim"] is True
        assert d["evaluation"]["has_metric"] is True

    def test_answer_to_dict_without_evaluation(self) -> None:
        a = InterviewAnswer(id="a-1", session_id="s-1", question_id="q-1", text="Text")
        d = a.to_dict()
        assert "evaluation" not in d

    def test_feedback_to_dict(self) -> None:
        f = InterviewFeedback(
            id="f-1",
            question_id="q-1",
            answer_id="a-1",
            missing=("metric",),
            improvement_recommendation="Add a metric.",
        )
        d = f.to_dict()
        assert d["missing"] == ["metric"]
        assert d["improvement_recommendation"] == "Add a metric."

    def test_metrics_to_dict(self) -> None:
        m = SessionMetrics(total_questions=5, answered_questions=3)
        d = m.to_dict()
        assert d["total_questions"] == 5
        assert d["answered_questions"] == 3

    def test_summary_to_dict(self) -> None:
        s = InterviewSummary(strong_answers=3, weak_answers=1)
        d = s.to_dict()
        assert d["strong_answers"] == 3
        assert d["weak_answers"] == 1

    def test_report_to_dict(self) -> None:
        report = InterviewReport(
            id="r-1",
            session_id="s-1",
            profile_id="p-1",
            plan_ref="plan-1",
            summary=InterviewSummary(total_questions=5),
            session_metrics=SessionMetrics(answered_questions=4),
            strengths=("Clear communication",),
            weaknesses=("Needs metrics",),
            recommendations=("Practice STAR format",),
        )
        d = report.to_dict()
        assert d["summary"]["total_questions"] == 5
        assert d["session_metrics"]["answered_questions"] == 4
        assert d["strengths"] == ["Clear communication"]

    def test_report_to_json(self) -> None:
        report = InterviewReport(
            id="r-1",
            session_id="s-1",
            profile_id="p-1",
            plan_ref="plan-1",
            summary=InterviewSummary(),
            session_metrics=SessionMetrics(),
        )
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["id"] == "r-1"


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------


class TestEdgeCases:

    def test_empty_answers_in_session(self) -> None:
        session = InterviewSession(
            id="s-1",
            plan_ref="plan-1",
            profile_id="p-1",
            questions=(
                InterviewQuestionInstance(id="q-1", session_id="s-1", question_text="Q", category="technical"),
            ),
        )
        assert session.answer_count == 0
        assert session.question_count == 1

    def test_completed_session_with_all_fields(self) -> None:
        answer = InterviewAnswer(
            id="a-1",
            session_id="s-1",
            question_id="q-1",
            text="Reduced costs by 40%.",
            answered_at="2026-01-01T10:05:00Z",
            duration_seconds=300,
            evaluation=AnswerEvaluation(
                covers_claim=True,
                has_metric=True,
                cites_evidence=True,
                follows_structure=True,
                matches_question_competencies=True,
            ),
            feedback=InterviewFeedback(
                id="f-1",
                question_id="q-1",
                answer_id="a-1",
                improvement_recommendation="Well done. Add more context.",
            ),
        )
        session = InterviewSession(
            id="s-1",
            plan_ref="plan-1",
            profile_id="p-1",
            state=SessionState.COMPLETED,
            questions=(
                InterviewQuestionInstance(
                    id="q-1", session_id="s-1", question_text="Q", category="technical"
                ),
            ),
            answers=(answer,),
            started_at="2026-01-01T10:00:00Z",
            completed_at="2026-01-01T10:30:00Z",
            metrics=SessionMetrics(total_questions=1, answered_questions=1),
            summary=InterviewSummary(
                total_questions=1,
                answered_questions=1,
                covered_claims=1,
                strong_answers=1,
            ),
        )
        assert session.state == SessionState.COMPLETED
        assert session.metrics is not None
        assert session.summary is not None
        assert session.answers[0].evaluation is not None

    def test_deterministic_defaults(self) -> None:
        s1 = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        s2 = InterviewSession(id="s-1", plan_ref="plan-1", profile_id="p-1")
        assert s1.to_dict() == s2.to_dict()

    def test_evidence_in_question_instance(self) -> None:
        """QuestionInstance evidence_citations use ADR-002 ref contract."""
        citation = EvidenceCitation(
            element_type="skill", element_id="skill-python", quote="Python"
        )
        q = InterviewQuestionInstance(
            id="q-1",
            session_id="s-1",
            question_text="Tell me about Python.",
            category="technical",
            evidence_citations=(citation,),
        )
        assert q.evidence_citations[0].source_ref() == {"id": "skill-python", "type": "skill"}
        assert q.evidence_citations[0].quote == "Python"


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------


class TestExceptions:

    def test_interview_session_error_is_interview_error(self) -> None:
        from careeros import InterviewError

        assert issubclass(InterviewSessionError, InterviewError)

    def test_invalid_session_state_error_is_interview_session_error(self) -> None:
        assert issubclass(InvalidSessionStateError, InterviewSessionError)

    def test_invalid_answer_error_is_interview_session_error(self) -> None:
        assert issubclass(InvalidAnswerError, InterviewSessionError)

    def test_invalid_session_state_error_message(self) -> None:
        exc = InvalidSessionStateError("Cannot transition from draft to completed")
        assert "draft" in str(exc)

    def test_invalid_answer_error_message(self) -> None:
        exc = InvalidAnswerError("Answer text cannot be empty")
        assert "empty" in str(exc)


# --------------------------------------------------------------------------
# Facade exports
# --------------------------------------------------------------------------


class TestFacadeExports:

    def test_session_state_accessible_from_careeros(self) -> None:
        assert SessionState.DRAFT.value == "draft"

    def test_interview_session_accessible_from_careeros(self) -> None:
        from careeros import InterviewSession as FacadeSession

        assert FacadeSession is InterviewSession

    def test_interview_report_accessible_from_careeros(self) -> None:
        from careeros import InterviewReport as FacadeReport

        assert FacadeReport is InterviewReport

    def test_all_simulation_types_exported_from_careeros(self) -> None:
        from careeros import (
            AnswerEvaluation as AE,
            InterviewAnswer as IA,
            InterviewFeedback as IF,
            InterviewQuestionInstance as IQI,
            InterviewReport as IR,
            InterviewSession as IS,
            InterviewSessionError as ISE,
            InterviewSummary as ISu,
            InvalidAnswerError as IAE,
            InvalidSessionStateError as ISSE,
            SessionMetrics as SM,
            SessionState as SS,
        )
        assert AE is not None
        assert IA is not None
        assert IF is not None
        assert IQI is not None
        assert IR is not None
        assert IS is not None
        assert ISE is not None
        assert ISu is not None
        assert IAE is not None
        assert ISSE is not None
        assert SM is not None
        assert SS is not None