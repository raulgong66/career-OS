"""M1.17.4 — Interview Simulation answer evaluation engine tests.

Covers the public evaluation contract from
``docs/platform-beta/interview-simulation/08-answer-evaluation-design.md``:
the pipeline stages (coverage, evidence, claim alignment, STAR, measurability,
consistency), the public inputs/outputs (``AnswerEvaluation``,
``InterviewFeedback``, ``EvaluationSummary``), the domain exceptions, rule
registry integration, determinism, immutability, and facade exports.
"""

from __future__ import annotations

import pytest

from careeros import (
    EVALUATION_RULE_IDS,
    AnswerEvaluation,
    EvaluationEngine,
    EvaluationPreconditionError,
    EvaluationSummary,
    EvidenceCitation,
    InterviewAnswer,
    InterviewQuestionInstance,
    InterviewSession,
    InterviewSessionError,
    InvalidAnswerError,
    InvalidClaimError,
    InvalidQuestionError,
    MissingEvidenceReferenceError,
    QuestionType,
)
from careeros.reasoning import Rule, RuleRegistry

STRONG = (
    "Situation: our platform had slow deployments. My task was to own "
    "reliability engineering and cut the lead time. As the lead engineer I "
    "implemented automated pipelines, which reduced deployment time by 60%. "
    "The result saved the team 2 million hours and the project was a clear "
    "success."
)
VAGUE = "I don't know, I am not sure about this question."
METRIC_ONLY = "I achieved a 40% improvement in efficiency during the migration."


def _question(
    qid: str = "q1",
    category: QuestionType = QuestionType.BEHAVIORAL,
    text: str = (
        "Describe how you led a project that reduced deployment time and "
        "improved reliability."
    ),
    competency_ids: tuple[str, ...] = ("reliability-engineering",),
    context_refs: tuple[dict[str, str], ...] = (
        {"id": "exp-1", "type": "experience"},
    ),
    evidence_citations: tuple[EvidenceCitation, ...] = (
        EvidenceCitation(
            element_type="experience",
            element_id="exp-1",
            quote="Reduced deployment time by 60%",
        ),
    ),
) -> InterviewQuestionInstance:
    return InterviewQuestionInstance(
        id=f"s-1:{qid}",
        session_id="s-1",
        question_text=text,
        category=category.value,
        competency_ids=competency_ids,
        context_refs=context_refs,
        evidence_citations=evidence_citations,
    )


def _answer(
    question: InterviewQuestionInstance,
    text: str,
    session_id: str = "s-1",
    answer_id: str = "a-1",
) -> InterviewAnswer:
    return InterviewAnswer(
        id=answer_id,
        session_id=session_id,
        question_id=question.id,
        text=text,
    )


@pytest.fixture
def engine() -> EvaluationEngine:
    return EvaluationEngine()


# --------------------------------------------------------------------------
# evaluate_answer — pipeline signals
# --------------------------------------------------------------------------


class TestEvaluateAnswer:

    def test_strong_answer_activates_all_signals(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(_answer(q, STRONG), q, None)
        assert evaluation.covers_claim is True
        assert evaluation.cites_evidence is True
        assert evaluation.has_metric is True
        assert evaluation.follows_structure is True
        assert evaluation.matches_question_competencies is True
        assert [c.element_id for c in evaluation.citations] == ["exp-1"]

    def test_vague_answer_has_no_signals(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(_answer(q, VAGUE), q, None)
        assert evaluation.covers_claim is False
        assert evaluation.cites_evidence is False
        assert evaluation.has_metric is False
        assert evaluation.follows_structure is False
        assert evaluation.matches_question_competencies is False
        assert evaluation.citations == ()

    def test_coverage_references_question_intent(self, engine: EvaluationEngine) -> None:
        q = _question(text="Explain the approach you take to incident response.")
        on_topic = engine.evaluate_answer(
            _answer(q, "My approach to incident response follows a clear runbook."), q, None
        )
        off_topic = engine.evaluate_answer(
            _answer(q, "My favorite movie is about space exploration."), q, None
        )
        assert on_topic.covers_claim is True
        assert off_topic.covers_claim is False

    def test_evidence_reference_by_quote(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(
            _answer(q, "It was straightforward: we reduced deployment time by 60%."), q, None
        )
        assert evaluation.cites_evidence is True
        assert evaluation.citations[0].source_ref() == {"id": "exp-1", "type": "experience"}

    def test_evidence_reference_by_element_id(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(
            _answer(q, "The numbers came from exp-1 which I owned."), q, None
        )
        assert evaluation.cites_evidence is True

    def test_no_evidence_reference(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(
            _answer(q, "I handled the migration without any canonical source."), q, None
        )
        assert evaluation.cites_evidence is False
        assert evaluation.citations == ()

    def test_claim_alignment_references_competencies(self, engine: EvaluationEngine) -> None:
        q = _question()
        aligned = engine.evaluate_answer(
            _answer(q, "Reliability engineering is exactly what I did."), q, None
        )
        not_aligned = engine.evaluate_answer(
            _answer(q, "I did a little bit of everything."), q, None
        )
        assert aligned.matches_question_competencies is True
        assert not_aligned.matches_question_competencies is False

    def test_measurability_reuses_core_service(self, engine: EvaluationEngine) -> None:
        q = _question()
        with_metric = engine.evaluate_answer(
            _answer(q, "I increased uptime by 15%."), q, None
        )
        without_metric = engine.evaluate_answer(
            _answer(q, "I was responsible for coordination."), q, None
        )
        assert with_metric.has_metric is True
        assert without_metric.has_metric is False

    @pytest.mark.parametrize("category", [
        QuestionType.BEHAVIORAL,
        QuestionType.LEADERSHIP,
        QuestionType.PROJECT_DEEP_DIVE,
    ])
    def test_star_requires_two_components(
        self, engine: EvaluationEngine, category: QuestionType
    ) -> None:
        q = _question(category=category)
        star = engine.evaluate_answer(
            _answer(q, "Situation: it was critical. Task: I owned it. Action: I led it."), q, None
        )
        no_star = engine.evaluate_answer(_answer(q, "It went fine, generally speaking."), q, None)
        assert star.follows_structure is True
        assert no_star.follows_structure is False

    def test_technical_question_requires_one_component(
        self, engine: EvaluationEngine
    ) -> None:
        q = _question(category=QuestionType.TECHNICAL)
        structured = engine.evaluate_answer(_answer(q, "I implemented the solution."), q, None)
        assert structured.follows_structure is True

    def test_career_motivation_is_not_structure_checked(
        self, engine: EvaluationEngine
    ) -> None:
        q = _question(category=QuestionType.CAREER_MOTIVATION)
        evaluation = engine.evaluate_answer(_answer(q, "I want to keep growing."), q, None)
        assert evaluation.follows_structure is False


# --------------------------------------------------------------------------
# evaluate_answer — validation failures
# --------------------------------------------------------------------------


class TestAnswerValidation:

    def test_empty_answer_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        with pytest.raises(InvalidAnswerError):
            engine.evaluate_answer(_answer(q, "   "), q, None)

    def test_non_answer_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        with pytest.raises(InvalidAnswerError):
            engine.evaluate_answer({"not": "an answer"}, q, None)

    def test_wrong_session_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        session = InterviewSession(id="s-1", plan_ref="p", profile_id="person-1")
        with pytest.raises(InvalidAnswerError):
            engine.evaluate_answer(_answer(q, STRONG, session_id="other"), q, session)

    def test_missing_question_and_session_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        with pytest.raises(InvalidQuestionError):
            engine.evaluate_answer(_answer(q, STRONG), None, None)

    def test_mismatched_question_raises(self, engine: EvaluationEngine) -> None:
        answer = _answer(_question("q1"), STRONG)
        other = _question("q2")
        with pytest.raises(InvalidQuestionError):
            engine.evaluate_answer(answer, other, None)

    def test_question_from_other_session_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        q = InterviewQuestionInstance(
            id=q.id, session_id="s-9", question_text=q.question_text,
            category=q.category, competency_ids=q.competency_ids,
            context_refs=q.context_refs, evidence_citations=q.evidence_citations,
        )
        session = InterviewSession(id="s-1", plan_ref="p", profile_id="person-1")
        with pytest.raises(InvalidQuestionError):
            engine.evaluate_answer(_answer(q, STRONG), q, session)


class TestClaimMetadataValidation:

    @pytest.mark.parametrize("context_refs", [
        ({"type": "experience"},),
        ({"id": "exp-1"},),
        ("not-a-dict",),
    ])
    def test_malformed_context_ref_raises(
        self, engine: EvaluationEngine, context_refs: object
    ) -> None:
        q = _question(context_refs=context_refs)  # type: ignore[arg-type]
        with pytest.raises(InvalidClaimError):
            engine.evaluate_answer(_answer(q, STRONG), q, None)

    def test_empty_competency_reference_raises(self, engine: EvaluationEngine) -> None:
        q = _question(competency_ids=("",))
        with pytest.raises(InvalidClaimError):
            engine.evaluate_answer(_answer(q, STRONG), q, None)


class TestEvidenceValidation:

    def test_blank_evidence_id_raises(self, engine: EvaluationEngine) -> None:
        q = _question(
            evidence_citations=(EvidenceCitation(element_type="skill", element_id=""),)
        )
        with pytest.raises(MissingEvidenceReferenceError):
            engine.evaluate_answer(_answer(q, STRONG), q, None)

    def test_non_canonical_element_type_raises(self, engine: EvaluationEngine) -> None:
        q = _question(
            evidence_citations=(
                EvidenceCitation(element_type="session", element_id="s-1"),
            )
        )
        with pytest.raises(MissingEvidenceReferenceError):
            engine.evaluate_answer(_answer(q, STRONG), q, None)

    def test_session_owned_fragment_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        with pytest.raises(MissingEvidenceReferenceError):
            engine.evaluate_answer(
                _answer(q, "My evidence is the question s-1:q1 itself."), q, None
            )


# --------------------------------------------------------------------------
# build_feedback
# --------------------------------------------------------------------------


class TestBuildFeedback:

    def test_feedback_shape(self, engine: EvaluationEngine) -> None:
        q = _question()
        feedback = engine.build_feedback(_answer(q, STRONG), q, None)
        assert feedback.id == "a-1:feedback"
        assert feedback.question_id == q.id
        assert feedback.answer_id == "a-1"
        assert isinstance(feedback, object)

    def test_strong_answer_has_no_missing_signal(self, engine: EvaluationEngine) -> None:
        q = _question()
        feedback = engine.build_feedback(_answer(q, STRONG), q, None)
        assert feedback.missing == ()
        assert feedback.improvement_recommendation is None
        assert feedback.citations[0].element_id == "exp-1"

    def test_vague_answer_lists_missing_signals(self, engine: EvaluationEngine) -> None:
        q = _question()
        feedback = engine.build_feedback(_answer(q, VAGUE), q, None)
        assert feedback.missing == ("coverage", "evidence", "structure")
        assert feedback.improvement_recommendation is not None

    def test_technical_answer_flags_missing_measurable_outcome(
        self, engine: EvaluationEngine
    ) -> None:
        q = _question(category=QuestionType.TECHNICAL)
        feedback = engine.build_feedback(
            _answer(q, "I worked on the project as part of the team."), q, None
        )
        assert "measurable outcome" in feedback.missing

    def test_contradiction_adds_consistency_signal(self, engine: EvaluationEngine) -> None:
        q = _question()
        feedback = engine.build_feedback(
            _answer(
                q,
                "We increased revenue last year but decreased profits in the same period.",
            ),
            q,
            None,
        )
        assert "consistency" in feedback.missing

    def test_mismatched_evidence_adds_alignment_advisory(
        self, engine: EvaluationEngine
    ) -> None:
        q = _question()
        text = "I reduced deployment time by 60% and cross-checked experience:exp-9."
        evaluation = engine.evaluate_answer(_answer(q, text), q, None)
        assert evaluation.cites_evidence is True
        feedback = engine.build_feedback(_answer(q, text), q, None)
        assert "evidence" in feedback.missing


# --------------------------------------------------------------------------
# evaluate_session
# --------------------------------------------------------------------------


def _session_with(*texts: str) -> InterviewSession:
    from careeros import InterviewPlan, InterviewQuestion, SessionEngine

    questions = tuple(
        InterviewQuestion(
            id=f"q{index + 1}",
            category=QuestionType.BEHAVIORAL,
            text=(
                "Describe how you led a project that reduced deployment time "
                "and improved reliability."
            ),
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
        for index in range(len(texts))
    )
    plan = InterviewPlan(
        profile_version="v1",
        person_id="person-1",
        target_role="Platform Engineer",
        questions=questions,
    )
    session_engine = SessionEngine()
    session = session_engine.start_session(session_engine.create_session(plan, "s-1"))
    for text in texts:
        question = session_engine.next_question(session)
        session = session_engine.submit_answer(
            session,
            InterviewAnswer(
                id=f"{session.id}:{question.id}:answer",
                session_id=session.id,
                question_id=question.id,
                text=text,
            ),
        )
    return session_engine.complete_session(session)


class TestEvaluateSession:

    def test_aggregates_signals(self, engine: EvaluationEngine) -> None:
        summary = engine.evaluate_session(_session_with(STRONG, VAGUE))
        assert isinstance(summary, EvaluationSummary)
        assert summary.total_answers == 2
        assert summary.coverage == 1
        assert summary.evidence == 1
        assert summary.claim_alignment == 1
        assert summary.measurability == 1
        assert summary.structure == 1
        assert summary.inconsistent_answers == 0

    def test_counts_inconsistent_answers(self, engine: EvaluationEngine) -> None:
        summary = engine.evaluate_session(_session_with(STRONG, METRIC_ONLY))
        assert summary.inconsistent_answers == 1
        assert summary.measurability == 2

    def test_reuses_stored_evaluations(self, engine: EvaluationEngine) -> None:
        session = _session_with(VAGUE)
        answer = session.answers[0]
        stored = InterviewAnswer(
            id=answer.id,
            session_id=answer.session_id,
            question_id=answer.question_id,
            text=answer.text,
            evaluation=AnswerEvaluation(
                covers_claim=True,
                has_metric=True,
                cites_evidence=True,
                follows_structure=True,
                matches_question_competencies=True,
            ),
        )
        session = InterviewSession(
            id=session.id, plan_ref=session.plan_ref, profile_id=session.profile_id,
            state=session.state, questions=session.questions, answers=(stored,),
        )
        summary = engine.evaluate_session(session)
        assert summary.coverage == 1
        assert summary.evidence == 1
        assert summary.claim_alignment == 1
        assert summary.measurability == 1

    def test_non_session_raises(self, engine: EvaluationEngine) -> None:
        with pytest.raises(EvaluationPreconditionError):
            engine.evaluate_session({"not": "a session"})


# --------------------------------------------------------------------------
# Rule registry integration
# --------------------------------------------------------------------------


class _MarkerRule(Rule):

    def __init__(self, rule_id: str) -> None:
        self._rule_id = rule_id

    @property
    def id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._rule_id

    @property
    def description(self) -> str:
        return "Marker rule for evaluation registry tests."

    def dependencies(self) -> list[str]:
        return []

    def execute(self, context) -> list:  # noqa: ANN001
        return []


def _full_registry() -> RuleRegistry:
    registry = RuleRegistry()
    for rule_id in EVALUATION_RULE_IDS:
        registry.register(_MarkerRule(rule_id))
    return registry


class TestRuleRegistry:

    def test_evaluates_without_registry(self, engine: EvaluationEngine) -> None:
        q = _question()
        evaluation = engine.evaluate_answer(_answer(q, STRONG), q, None)
        assert evaluation.covers_claim is True

    def test_registry_with_all_rules_is_equivalent(
        self, engine: EvaluationEngine
    ) -> None:
        q = _question()
        baseline = engine.evaluate_answer(_answer(q, STRONG), q, None)
        with_registry = engine.evaluate_answer(
            _answer(q, STRONG), q, None, _full_registry()
        )
        assert with_registry.to_dict() == baseline.to_dict()

    def test_registry_missing_rules_raises(self, engine: EvaluationEngine) -> None:
        registry = RuleRegistry()
        registry.register(_MarkerRule(EVALUATION_RULE_IDS[0]))
        q = _question()
        with pytest.raises(EvaluationPreconditionError):
            engine.evaluate_answer(_answer(q, STRONG), q, None, registry)

    def test_non_registry_rule_set_raises(self, engine: EvaluationEngine) -> None:
        q = _question()
        with pytest.raises(EvaluationPreconditionError):
            engine.evaluate_answer(_answer(q, STRONG), q, None, {"not": "a registry"})


# --------------------------------------------------------------------------
# Determinism & immutability
# --------------------------------------------------------------------------


class TestDeterminismAndImmutability:

    def test_evaluation_is_deterministic(self, engine: EvaluationEngine) -> None:
        q = _question()
        first = engine.evaluate_answer(_answer(q, STRONG), q, None)
        second = engine.evaluate_answer(_answer(q, STRONG), q, None)
        assert first.to_dict() == second.to_dict()

    def test_evaluate_does_not_mutate_inputs(self, engine: EvaluationEngine) -> None:
        q = _question()
        answer = _answer(q, STRONG)
        q_before = q.to_dict()
        answer_before = answer.to_dict()
        engine.evaluate_answer(answer, q, None)
        engine.build_feedback(answer, q, None)
        assert q.to_dict() == q_before
        assert answer.to_dict() == answer_before


# --------------------------------------------------------------------------
# Facade exports
# --------------------------------------------------------------------------


class TestFacadeExports:

    def test_engine_exported_from_careeros(self) -> None:
        assert EvaluationEngine is not None

    def test_engine_exported_from_interview_packages(self) -> None:
        from careeros.interview import EvaluationEngine as FromInterview
        from careeros.interview.simulation import EvaluationEngine as FromSimulation
        assert FromInterview is EvaluationEngine
        assert FromSimulation is EvaluationEngine

    def test_evaluation_summary_and_rule_ids_exported(self) -> None:
        assert EVALUATION_RULE_IDS == (
            "evaluation.coverage",
            "evaluation.evidence",
            "evaluation.claim",
            "evaluation.star",
            "evaluation.measurability",
            "evaluation.consistency",
        )
        assert EvaluationSummary().to_dict()["total_answers"] == 0

    def test_new_exceptions_are_session_errors(self) -> None:
        for exc in (
            InvalidQuestionError,
            MissingEvidenceReferenceError,
            InvalidClaimError,
            EvaluationPreconditionError,
        ):
            assert issubclass(exc, InterviewSessionError)
