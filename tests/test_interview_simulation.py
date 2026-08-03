"""Interview Simulation domain foundation tests."""

from __future__ import annotations

import unittest

from careeros import InterviewEngine
from careeros.interview.simulation import (
    EvaluationEngine,
    InterviewAnswer,
    InterviewReport,
    InterviewSessionState,
    InterviewQuestionInstance,
    SessionEngine,
)
from careeros.interview.simulation.exceptions import (
    InvalidQuestionError,
    InvalidSessionStateError,
)


def make_profile() -> dict:
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


class InterviewSimulationDomainTests(unittest.TestCase):
    def test_session_lifecycle_and_answer_progression(self) -> None:
        engine = InterviewEngine()
        plan = engine.generate_plan(make_profile())
        session_engine = SessionEngine()

        session = session_engine.create_session(plan=plan, session_id="session-1")
        self.assertEqual(session.state, InterviewSessionState.DRAFT)
        self.assertEqual(session.question_count, plan.question_count)

        session = session_engine.start_session(session)
        if plan.question_count == 0:
            self.assertEqual(session.state, InterviewSessionState.COMPLETED)
            return

        self.assertEqual(session.state, InterviewSessionState.IN_PROGRESS)
        current = session.current_question_instance()
        self.assertIsInstance(current, InterviewQuestionInstance)
        self.assertEqual(current.index, 1)

        answer = InterviewAnswer(
            question_id=current.question.id,
            text="I built a platform that reduced costs by using automation and cloud services.",
            evidence_references=tuple(ref.source_ref() for ref in current.question.evidence_citations),
        )
        session = session_engine.submit_answer(session, answer)
        self.assertEqual(session.answered_count, 1)

        session = session_engine.next_question(session)
        self.assertTrue(
            session.current_question_index == 1
            or session.state == InterviewSessionState.COMPLETED
        )

        if session.state == InterviewSessionState.IN_PROGRESS:
            session = session_engine.complete_session(session)
            self.assertEqual(session.state, InterviewSessionState.COMPLETED)

        summary = session_engine.build_summary(session)
        self.assertEqual(summary.session_id, session.session_id)
        self.assertEqual(summary.answered_questions, session.answered_count)
        report = session_engine.build_report(session)
        self.assertIsInstance(report, InterviewReport)
        self.assertGreaterEqual(report.summary.average_score, 0)

    def test_invalid_transitions_raise_errors(self) -> None:
        engine = InterviewEngine()
        plan = engine.generate_plan(make_profile())
        session_engine = SessionEngine()

        session = session_engine.create_session(plan=plan, session_id="session-2")
        with self.assertRaises(InvalidSessionStateError):
            session_engine.submit_answer(session, InterviewAnswer(question_id="q-1", text="text"))

        session = session_engine.start_session(session)
        current = session.current_question_instance()
        self.assertIsNotNone(current)

        wrong_answer = InterviewAnswer(question_id="wrong-id", text="text")
        with self.assertRaises(InvalidQuestionError):
            session_engine.submit_answer(session, wrong_answer)

        session = session_engine.pause_session(session)
        with self.assertRaises(InvalidSessionStateError):
            session_engine.start_session(session)
        session = session_engine.resume_session(session)
        self.assertEqual(session.state, InterviewSessionState.IN_PROGRESS)

    def test_evaluation_determinism(self) -> None:
        engine = EvaluationEngine()
        plan = InterviewEngine().generate_plan(make_profile())
        self.assertGreater(plan.question_count, 0)

        session_engine = SessionEngine()
        session = session_engine.create_session(plan=plan, session_id="session-det")
        session = session_engine.start_session(session)
        current = session.current_question_instance()
        self.assertIsNotNone(current)

        answer = InterviewAnswer(
            question_id=current.question.id,
            text="I led a project to deploy a platform using Kubernetes and automation.",
            evidence_references=tuple(ref.source_ref() for ref in current.question.evidence_citations),
        )
        evaluation_1 = engine.evaluate_answer(current.question, answer)
        evaluation_2 = engine.evaluate_answer(current.question, answer)

        self.assertEqual(evaluation_1.overall_score, evaluation_2.overall_score)
        self.assertEqual(evaluation_1.to_dict(), evaluation_2.to_dict())
