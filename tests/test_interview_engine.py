"""M1.14 — Interview Intelligence deterministic engine tests.

Covers question generation, evidence grounding (mandatory), suggested-answer
outline structure, question categories, deterministic output, empty-profile
behavior, multiple experiences, cap behavior, Core reuse (concept taxonomy,
knowledge graph), and regression against the real sample profile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from careeros import (
    Competency,
    InterviewEngine,
    InterviewPlan,
    QuestionType,
    SuggestedAnswer,
)
from careeros.exceptions import CareerOSException
from careeros.interview.exceptions import InvalidProfileError
from careeros.profile_loader import ProfileLoader
from careeros.schema_loader import SchemaLoader


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def make_profile() -> dict:
    """A canonical profile with rich, cross-linked evidence."""
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-tester",
            "names": [{"value": "Test Person", "usage": "professional"}],
            "positioning": {"headline": "Senior Platform Engineer"},
        },
        "organizations": [
            {"id": "org-acme", "name": "ACME Corp"},
            {"id": "org-beta", "name": "Beta Labs"},
        ],
        "experiences": [
            {
                "id": "exp-acme",
                "title": "Platform Engineer",
                "organizationRefs": [{"id": "org-acme", "type": "organization"}],
                "scope": (
                    "Led migration of 200 services to Kubernetes and AWS, "
                    "reducing infrastructure costs by 40%."
                ),
            },
            {
                "id": "exp-beta",
                "title": "Founder",
                "organizationRefs": [{"id": "org-beta", "type": "organization"}],
                "scope": (
                    "Founded a startup and built the product end to end "
                    "with Python and Django."
                ),
            },
        ],
        "projects": [
            {
                "id": "project-platform",
                "name": "Platform Reboot",
                "description": (
                    "Rebuilt the deployment platform on Kubernetes with GitOps."
                ),
            }
        ],
        "skills": [
            {
                "id": "skill-kubernetes",
                "name": "Kubernetes",
                "description": "AWS, GCP, container orchestration, helm",
                "extensions": {
                    "experienceEvidence": [{"experienceId": "exp-acme"}]
                },
            },
            {
                "id": "skill-python",
                "name": "Python",
                "description": "Django, REST APIs, automation",
                "extensions": {
                    "experienceEvidence": [{"experienceId": "exp-beta"}]
                },
            },
        ],
        "achievements": [
            {
                "id": "achievement-cost-reduction",
                "statement": (
                    "Reduced infrastructure costs by 40% through the "
                    "Kubernetes migration."
                ),
                "contextRefs": [{"id": "exp-acme", "type": "experience"}],
            }
        ],
        "education": [],
        "certifications": [],
    }


@pytest.fixture
def engine() -> InterviewEngine:
    return InterviewEngine()


@pytest.fixture
def profile() -> dict:
    return make_profile()


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _all_element_refs(profile: dict) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for collection in (
        "experiences",
        "projects",
        "skills",
        "achievements",
        "education",
        "certifications",
    ):
        for element in profile.get(collection, []):
            refs.add((collection.rstrip("s") if collection != "experiences" else "experience", str(element.get("id"))))
    person = profile.get("person", {})
    if person.get("id"):
        refs.add(("person", str(person["id"])))
    return refs


# --------------------------------------------------------------------------
# Question generation
# --------------------------------------------------------------------------


def test_plan_generation_returns_questions(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    assert isinstance(plan, InterviewPlan)
    assert plan.question_count > 0


def test_all_categories_present_when_evidence_supports(
    engine: InterviewEngine, profile: dict
) -> None:
    plan = engine.generate_plan(profile, target_role="Platform Engineer")
    categories = {q.category for q in plan.questions}
    assert categories == set(QuestionType)


def test_questions_only_generated_with_evidence(engine: InterviewEngine) -> None:
    profile = make_profile()
    profile["skills"] = []
    profile["experiences"] = []
    profile["projects"] = []
    profile["achievements"] = []
    profile["person"]["positioning"] = {}
    plan = engine.generate_plan(profile)
    assert plan.question_count == 0


def test_no_technical_questions_without_skills(engine: InterviewEngine) -> None:
    profile = make_profile()
    profile["skills"] = []
    plan = engine.generate_plan(profile)
    categories = [q.category for q in plan.questions]
    assert QuestionType.TECHNICAL not in categories


# --------------------------------------------------------------------------
# Evidence grounding (mandatory)
# --------------------------------------------------------------------------


def test_every_question_has_evidence_citations(
    engine: InterviewEngine, profile: dict
) -> None:
    plan = engine.generate_plan(profile)
    assert plan.question_count > 0
    for question in plan.questions:
        assert question.evidence_citations, (
            f"Question {question.id} has no evidence citations"
        )


def test_citations_resolve_to_canonical_profile_elements(
    engine: InterviewEngine, profile: dict
) -> None:
    plan = engine.generate_plan(profile)
    refs = _all_element_refs(profile)
    for question in plan.questions:
        for citation in question.evidence_citations:
            assert (
                citation.element_type,
                citation.element_id,
            ) in refs, (
                f"{question.id} cites unknown element "
                f"({citation.element_type}, {citation.element_id})"
            )
            assert citation.source_ref() == {
                "id": citation.element_id,
                "type": citation.element_type,
            }


def test_context_refs_match_evidence(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    for question in plan.questions:
        citation_refs = {frozenset(c.source_ref().items()) for c in question.evidence_citations}
        assert citation_refs, f"{question.id} has no citations"
        for ref in question.context_refs:
            assert frozenset(ref.items()) in citation_refs


def test_technical_question_anchored_to_experience(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    technical = [q for q in plan.questions if q.category == QuestionType.TECHNICAL]
    assert technical
    for question in technical:
        types = {c.element_type for c in question.evidence_citations}
        assert "experience" in types
        assert "skill" in types
        assert question.template_id == "technical-skill-in-practice"


# --------------------------------------------------------------------------
# Suggested answer structure
# --------------------------------------------------------------------------


def test_suggested_answer_outline_structure(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    outline_keys = {"situation", "task", "action", "result", "evidence", "achievement"}
    for question in plan.questions:
        assert question.suggested_answer is not None
        outline = question.suggested_answer
        assert isinstance(outline, SuggestedAnswer)
        assert set(outline.to_dict().keys()) == outline_keys
        assert outline.evidence  # outline always cites its grounding


def test_suggested_answer_sources_from_profile(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    for question in plan.questions:
        outline = question.suggested_answer
        if outline.action:
            assert any(
                outline.action in (exp.get("scope") or "")
                or outline.action in (proj.get("description") or "")
                for exp in profile["experiences"]
                for proj in profile["projects"]
            )


def test_suggested_answer_includes_linked_achievement(
    engine: InterviewEngine, profile: dict
) -> None:
    plan = engine.generate_plan(profile)
    behavioral = [q for q in plan.questions if q.category == QuestionType.BEHAVIORAL]
    acme = next(
        q for q in behavioral if "exp-acme" in {c.element_id for c in q.evidence_citations}
    )
    assert acme.suggested_answer is not None
    assert "40%" in (acme.suggested_answer.result or "")
    assert "40%" in (acme.suggested_answer.achievement or "")


# --------------------------------------------------------------------------
# Deterministic output
# --------------------------------------------------------------------------


def test_plan_is_deterministic(engine: InterviewEngine, profile: dict) -> None:
    first = engine.generate_plan(profile, target_role="Platform Engineer").to_dict()
    second = engine.generate_plan(profile, target_role="Platform Engineer").to_dict()
    assert first == second


def test_plan_is_deterministic_across_instances(profile: dict) -> None:
    first = InterviewEngine().generate_plan(profile).to_dict()
    second = InterviewEngine().generate_plan(profile).to_dict()
    assert first == second


def test_question_ids_are_unique(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    ids = [q.id for q in plan.questions]
    assert len(ids) == len(set(ids))


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------


def test_empty_profile_yields_empty_plan(engine: InterviewEngine) -> None:
    plan = engine.generate_plan({})
    assert isinstance(plan, InterviewPlan)
    assert plan.question_count == 0
    assert plan.competencies == ()
    assert plan.person_id == "unknown"
    assert plan.profile_version == "unknown"


def test_multiple_experiences_yield_questions_per_experience(
    engine: InterviewEngine,
) -> None:
    profile = make_profile()
    profile["experiences"].append(
        {
            "id": "exp-third",
            "title": "SRE",
            "scope": "Ran on-call and reduced downtime with automation.",
        }
    )
    plan = engine.generate_plan(profile)
    behavioral = [q for q in plan.questions if q.category == QuestionType.BEHAVIORAL]
    cited_experiences = {
        c.element_id for q in behavioral for c in q.evidence_citations
    }
    assert {"exp-acme", "exp-beta"} <= cited_experiences
    assert len(behavioral) == 2  # capped


def test_max_questions_per_category_cap(profile: dict) -> None:
    plan = InterviewEngine(max_questions_per_category=1).generate_plan(profile)
    counts = {category: len(questions) for category, questions in plan.questions_by_category().items()}
    assert counts["technical"] == 1
    assert counts["behavioral"] == 1


def test_technical_questions_prefer_anchored_skills(profile: dict) -> None:
    profile["skills"].append(
        {
            "id": "skill-unmatched",
            "name": "Quantum Fortran Compilers",
            "description": "obscure toolchain with no experience evidence",
        }
    )
    plan = InterviewEngine(max_questions_per_category=3).generate_plan(profile)
    technical = [q for q in plan.questions if q.category == QuestionType.TECHNICAL]
    assert len(technical) == 3
    # Anchored skills come first; the unmatched skill uses the decision variant.
    assert technical[0].template_id == "technical-skill-in-practice"
    assert technical[1].template_id == "technical-skill-in-practice"
    assert technical[2].template_id == "technical-skill-decision"


def test_leadership_question_from_founder(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    leadership = [q for q in plan.questions if q.category == QuestionType.LEADERSHIP]
    assert leadership
    founder = next(
        q for q in leadership if any(c.element_id == "exp-beta" for c in q.evidence_citations)
    )
    assert "Founder" in founder.text


def test_invalid_profile_raises(engine: InterviewEngine) -> None:
    with pytest.raises(InvalidProfileError):
        engine.generate_plan("not a profile")  # type: ignore[arg-type]
    assert issubclass(InvalidProfileError, CareerOSException)


# --------------------------------------------------------------------------
# Core reuse
# --------------------------------------------------------------------------


def test_competency_mapping_reuses_concept_taxonomy(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    by_id = {c.id: c for c in plan.competencies}
    kubernetes = by_id["competency-skill-kubernetes"]
    assert isinstance(kubernetes, Competency)
    assert kubernetes.skill_ids == ("skill-kubernetes",)
    assert "container-platform" in kubernetes.concept_ids
    assert kubernetes.category == "infrastructure"


def test_competency_cites_skill_and_experience(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile)
    by_id = {c.id: c for c in plan.competencies}
    kubernetes = by_id["competency-skill-kubernetes"]
    cited = {(c.element_type, c.element_id) for c in kubernetes.evidence}
    assert ("skill", "skill-kubernetes") in cited
    assert ("experience", "exp-acme") in cited


def test_target_role_requirements_reuse_extractor(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile, target_role="Senior Kubernetes Engineer")
    assert "kubernetes" in plan.target_role_requirements


# --------------------------------------------------------------------------
# Plan metadata / future AI readiness
# --------------------------------------------------------------------------


def test_plan_carries_profile_version_and_person(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile, target_context_id="ctx-1")
    assert plan.profile_version == "1.0.0"
    assert plan.derived_from_profile_version == "1.0.0"
    assert plan.person_id == "person-tester"
    assert plan.target_context_id == "ctx-1"


def test_preparation_guide_from_plan(engine: InterviewEngine, profile: dict) -> None:
    plan = engine.generate_plan(profile, target_role="Platform Engineer")
    guide = plan_preparation_guide(plan)
    assert guide.id == "guide-1"
    assert guide.profile_id == "person-tester"
    assert guide.questions == plan.questions
    assert guide.competencies == plan.competencies


def plan_preparation_guide(plan: InterviewPlan):
    from careeros import PreparationGuide

    return PreparationGuide.from_plan(plan, guide_id="guide-1")


# --------------------------------------------------------------------------
# Regression: real sample profile
# --------------------------------------------------------------------------


def test_real_profile_end_to_end(repo_root: Path) -> None:
    loader = ProfileLoader(SchemaLoader(repo_root / "schemas"))
    profile = loader.load(repo_root / "profiles" / "raul-gongora-profile.yaml")
    engine = InterviewEngine()
    plan = engine.generate_plan(profile, target_role="Senior DevSecOps Specialist")
    assert plan.question_count > 0
    assert {q.category for q in plan.questions} == set(QuestionType)
    refs = _all_element_refs(profile)
    for question in plan.questions:
        for citation in question.evidence_citations:
            assert (
                citation.element_type,
                citation.element_id,
            ) in refs
    assert plan.to_dict() == engine.generate_plan(profile, target_role="Senior DevSecOps Specialist").to_dict()


def test_facade_exports_interview_api() -> None:
    from careeros import InterviewEngine, InterviewPlan, QuestionType, Competency

    assert InterviewEngine is not None
    assert InterviewPlan is not None
    assert QuestionType.TECHNICAL.value == "technical"
    assert Competency is not None
