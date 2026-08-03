"""Interview Intelligence — deterministic question engine.

``InterviewEngine`` is a pure, deterministic Core consumer: it reads a canonical
profile, builds a ``KnowledgeGraph`` (reused Core), maps competencies over the
Core concept taxonomy, and emits an ``InterviewPlan`` where every question is
evidence-backed and every answer outline is structured. No AI, no randomness,
no IO — identical profile in, identical plan out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from careeros.knowledge import KnowledgeGraph, KnowledgeGraphBuilder

from ..optimizer import CVOptimizer
from .competency import CompetencyMapper
from .domain import (
    CATEGORY_ORDER,
    Competency,
    EvidenceCitation,
    InterviewPlan,
    InterviewQuestion,
    QuestionType,
)
from .exceptions import InvalidProfileError, UnsupportedQuestionTypeError
from .question_builder import QuestionBuilder
from .templates import QUESTION_TEMPLATES, QuestionTemplate

_LEADERSHIP_MARKERS = (
    "lead", "led", "leadership", "founder", "ceo", "cto", "head of",
    "manager", "management", "director", "spearhead", "spearheaded",
    "owner", "founded", "responsible for", "overseeing",
)

_PROBLEM_SOLVING_MARKERS = (
    "solved", "solve", "solving", "complex", "challenge", "incident",
    "troubleshoot", "automated", "automation", "migrated", "migration",
    "reduced", "optimized", "optimisation", "optimization", "designed",
    "built", "refactored", "issue", "fix", "fixed", "resolved", "secured",
    "scaled", "scaling",
)


@dataclass(frozen=True)
class _Candidate:
    """Internal question candidate produced by a deterministic rule."""

    category: QuestionType
    template: QuestionTemplate
    values: dict[str, str]
    evidence: tuple[EvidenceCitation, ...]
    competency_ids: tuple[str, ...]
    motivation: str
    order_key: tuple[Any, ...]


class InterviewEngine:
    """Generate deterministic, evidence-backed interview plans from a profile."""

    def __init__(
        self,
        templates: Sequence[QuestionTemplate] | None = None,
        competency_mapper: CompetencyMapper | None = None,
        question_builder: QuestionBuilder | None = None,
        max_questions_per_category: int = 2,
    ) -> None:
        self.templates = tuple(templates) if templates is not None else QUESTION_TEMPLATES
        self.competency_mapper = competency_mapper or CompetencyMapper()
        self.question_builder = question_builder or QuestionBuilder()
        self.max_questions_per_category = max_questions_per_category

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        profile: dict[str, Any],
        *,
        target_role: str | None = None,
        target_context_id: str | None = None,
    ) -> InterviewPlan:
        """Build a deterministic ``InterviewPlan`` from a canonical profile."""
        if not isinstance(profile, dict):
            raise InvalidProfileError(
                "Interview engine requires a canonical profile dictionary"
            )

        graph = KnowledgeGraphBuilder().build(profile)
        competencies = self.competency_mapper.map(profile, graph=graph)
        candidates = self._generate_candidates(profile, graph, competencies, target_role)
        questions = self._instantiate(candidates)

        person = profile.get("person", {})
        return InterviewPlan(
            profile_version=str(profile.get("profileVersion") or "unknown"),
            person_id=str(person.get("id") or "unknown"),
            competencies=competencies,
            questions=questions,
            target_role=target_role,
            target_context_id=target_context_id,
            target_role_requirements=self._target_role_requirements(target_role),
            derived_from_profile_version=str(profile.get("profileVersion") or "unknown"),
        )

    @staticmethod
    def _target_role_requirements(target_role: str | None) -> tuple[str, ...]:
        """Reuse the Core requirement-extraction heuristic (no re-implementation)."""
        if not target_role:
            return ()
        return tuple(CVOptimizer.extract_requirements(target_role))

    def _generate_candidates(
        self,
        profile: dict[str, Any],
        graph: KnowledgeGraph,
        competencies: tuple[Competency, ...],
        target_role: str | None,
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        candidates.extend(self._technical_candidates(profile, graph, competencies))
        candidates.extend(self._behavioral_candidates(profile))
        candidates.extend(self._leadership_candidates(profile))
        candidates.extend(self._project_candidates(profile))
        candidates.extend(self._problem_solving_candidates(profile))
        candidates.extend(self._career_motivation_candidates(profile, target_role))
        return candidates

    def _instantiate(self, candidates: list[_Candidate]) -> tuple[InterviewQuestion, ...]:
        per_category: dict[QuestionType, list[_Candidate]] = {}
        for candidate in candidates:
            per_category.setdefault(candidate.category, []).append(candidate)

        questions: list[InterviewQuestion] = []
        for category in CATEGORY_ORDER:
            ordered = per_category.get(category, [])
            ordered = sorted(ordered, key=lambda c: c.order_key)
            for index, candidate in enumerate(ordered[: self.max_questions_per_category], start=1):
                questions.append(
                    self.question_builder.build_question(
                        candidate.template,
                        values=candidate.values,
                        evidence_citations=candidate.evidence,
                        competency_ids=candidate.competency_ids,
                        motivation=candidate.motivation,
                        question_id=f"q-{category.value}-{index:02d}",
                    )
                )
        return tuple(questions)

    def _template(self, category: QuestionType) -> QuestionTemplate:
        for template in self.templates:
            if template.category == category:
                return template
        raise UnsupportedQuestionTypeError(
            f"No template registered for question category: {category.value}"
        )

    def _template_by_id(
        self,
        template_id: str,
        category: QuestionType,
    ) -> QuestionTemplate:
        for template in self.templates:
            if template.template_id == template_id:
                return template
        return self._template(category)

    # ------------------------------------------------------------------
    # Technical (skill → experience evidence)
    # ------------------------------------------------------------------

    def _technical_candidates(
        self,
        profile: dict[str, Any],
        graph: KnowledgeGraph,
        competencies: tuple[Competency, ...],
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        by_id = self._skills_by_id(profile)
        for competency in competencies:
            skill = by_id.get(competency.skill_ids[0]) if competency.skill_ids else None
            if skill is None:
                continue
            experience = self._best_experience_for_skill(graph, skill, profile)
            skill_citation = EvidenceCitation(
                element_type="skill",
                element_id=skill["id"],
                quote=skill.get("name"),
            )
            if experience is not None:
                template = self._template_by_id(
                    "technical-skill-in-practice", QuestionType.TECHNICAL
                )
                citations = [skill_citation, self._experience_citation(experience)]
                motivation = (
                    f"Profile evidence: skill '{skill['name']}' is exercised in "
                    f"experience '{experience['id']}'."
                )
                values = self._experience_values(experience, profile)
                values["skill"] = skill.get("name", "")
                candidates.append(
                    _Candidate(
                        category=QuestionType.TECHNICAL,
                        template=template,
                        values=values,
                        evidence=tuple(citations),
                        competency_ids=(competency.id,),
                        motivation=motivation,
                        order_key=(1, competency.id, experience.get("id", "")),
                    )
                )
            else:
                template = self._template_by_id(
                    "technical-skill-decision", QuestionType.TECHNICAL
                )
                # Unanchored variant asks about the decision, not a specific role.
                candidates.append(
                    _Candidate(
                        category=QuestionType.TECHNICAL,
                        template=template,
                        values={"skill": skill.get("name", "")},
                        evidence=(skill_citation,),
                        competency_ids=(competency.id,),
                        motivation=f"Profile evidence: skill '{skill['name']}'.",
                        order_key=(2, competency.id),
                    )
                )
        return candidates

    def _best_experience_for_skill(
        self,
        graph: KnowledgeGraph,
        skill: dict[str, Any],
        profile: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Prefer authoritative graph edges, then deterministic token overlap."""
        graph_experiences = sorted(
            graph.experiences_using(skill.get("name", "")), key=lambda node: node.id
        )
        experiences = self._experiences_by_id(profile)
        if graph_experiences:
            for node in graph_experiences:
                experience = experiences.get(node.id)
                if experience is not None:
                    return experience

        tokens = set(CompetencyMapper.skill_tokens(skill))
        if not tokens:
            return None
        best: tuple[dict[str, Any], int] | None = None
        for experience in sorted(experiences.values(), key=lambda e: e.get("id", "")):
            scope = str(experience.get("scope") or "")
            overlap = len(
                tokens
                & {match for match in re.findall(r"[a-z0-9]+", scope.lower()) if len(match) >= 3}
            )
            if overlap > 0 and (best is None or overlap > best[1]):
                best = (experience, overlap)
        return best[0] if best else None

    # ------------------------------------------------------------------
    # Behavioral / Leadership / Project / Problem solving / Motivation
    # ------------------------------------------------------------------

    def _behavioral_candidates(self, profile: dict[str, Any]) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        template = self._template(QuestionType.BEHAVIORAL)
        for experience in self._sorted_experiences(profile):
            if not experience.get("scope"):
                continue
            candidates.append(
                _Candidate(
                    category=QuestionType.BEHAVIORAL,
                    template=template,
                    values=self._experience_values(experience, profile),
                    evidence=(self._experience_citation(experience),),
                    competency_ids=(),
                    motivation=f"Profile evidence: experience '{experience['id']}'.",
                    order_key=(experience.get("id", ""),),
                )
            )
        return candidates

    def _leadership_candidates(self, profile: dict[str, Any]) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        template = self._template(QuestionType.LEADERSHIP)
        for experience in self._sorted_experiences(profile):
            haystack = f"{experience.get('title', '')} {experience.get('scope', '')}".lower()
            if not any(marker in haystack for marker in _LEADERSHIP_MARKERS):
                continue
            candidates.append(
                _Candidate(
                    category=QuestionType.LEADERSHIP,
                    template=template,
                    values=self._experience_values(experience, profile),
                    evidence=(self._experience_citation(experience),),
                    competency_ids=(),
                    motivation=(
                        f"Profile evidence: experience '{experience['id']}' "
                        "shows leadership signals."
                    ),
                    order_key=(experience.get("id", ""),),
                )
            )
        return candidates

    def _project_candidates(self, profile: dict[str, Any]) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        template = self._template(QuestionType.PROJECT_DEEP_DIVE)
        for project in self._sorted_projects(profile):
            if not project.get("description"):
                continue
            values = {
                "project": project.get("name", ""),
                "situation": project.get("name"),
                "action": project.get("description"),
            }
            citation = EvidenceCitation(
                element_type="project",
                element_id=project["id"],
                quote=project.get("description"),
            )
            candidates.append(
                _Candidate(
                    category=QuestionType.PROJECT_DEEP_DIVE,
                    template=template,
                    values=values,
                    evidence=(citation,),
                    competency_ids=(),
                    motivation=f"Profile evidence: project '{project['id']}'.",
                    order_key=(project.get("id", ""),),
                )
            )
        return candidates

    def _problem_solving_candidates(self, profile: dict[str, Any]) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        template = self._template(QuestionType.PROBLEM_SOLVING)
        for experience in self._sorted_experiences(profile):
            haystack = f"{experience.get('title', '')} {experience.get('scope', '')}".lower()
            if not any(marker in haystack for marker in _PROBLEM_SOLVING_MARKERS):
                continue
            candidates.append(
                _Candidate(
                    category=QuestionType.PROBLEM_SOLVING,
                    template=template,
                    values=self._experience_values(experience, profile),
                    evidence=(self._experience_citation(experience),),
                    competency_ids=(),
                    motivation=f"Profile evidence: experience '{experience['id']}'.",
                    order_key=(experience.get("id", ""),),
                )
            )
        return candidates

    def _career_motivation_candidates(
        self, profile: dict[str, Any], target_role: str | None
    ) -> list[_Candidate]:
        person = profile.get("person", {})
        positioning = person.get("positioning", {}) or {}
        headline = positioning.get("headline")
        if not headline:
            return []

        person_id = str(person.get("id") or "person")
        person_citation = EvidenceCitation(
            element_type="person",
            element_id=person_id,
            quote=headline,
        )
        experiences = self._sorted_experiences(profile)
        experience = experiences[0] if experiences else None

        if target_role and experience is not None:
            template = self._template_by_id(
                "career-motivation-target", QuestionType.CAREER_MOTIVATION
            )
            values = self._experience_values(experience, profile)
            values["role"] = target_role
            citations = [person_citation, self._experience_citation(experience)]
            motivation = (
                f"Profile evidence: target role '{target_role}' and experience "
                f"'{experience['id']}'."
            )
            order_key = (experience.get("id", ""),)
        else:
            template = self._template_by_id(
                "career-motivation-direction", QuestionType.CAREER_MOTIVATION
            )
            values = {"headline": headline}
            citations = [person_citation]
            motivation = "Profile evidence: person positioning headline."
            order_key = ("person",)

        return [
            _Candidate(
                category=QuestionType.CAREER_MOTIVATION,
                template=template,
                values=values,
                evidence=tuple(citations),
                competency_ids=(),
                motivation=motivation,
                order_key=order_key,
            )
        ]

    # ------------------------------------------------------------------
    # Shared profile helpers (deterministic, no duplicate knowledge)
    # ------------------------------------------------------------------

    def _experience_values(
        self, experience: dict[str, Any], profile: dict[str, Any]
    ) -> dict[str, str]:
        title = experience.get("title", "")
        org = self._org_name(profile, experience)
        situation = f"{title} at {org}" if org else (title or None)
        achievement = self._linked_achievement(profile, experience.get("id"))
        values: dict[str, str] = {
            "experience": title or experience.get("id", ""),
            "situation": situation or "",
            "action": experience.get("scope") or "",
        }
        if achievement:
            values["result"] = achievement
            values["achievement"] = achievement
        return values

    def _experience_citation(self, experience: dict[str, Any]) -> EvidenceCitation:
        return EvidenceCitation(
            element_type="experience",
            element_id=experience.get("id", ""),
            quote=experience.get("scope"),
        )

    def _linked_achievement(self, profile: dict[str, Any], element_id: str) -> str | None:
        """Resolve an achievement linked to an element via canonical refs."""
        for achievement in self._sorted_achievements(profile):
            for ref in achievement.get("contextRefs", []) or []:
                if isinstance(ref, dict) and ref.get("id") == element_id:
                    statement = achievement.get("statement")
                    if statement:
                        return str(statement)
        element = self._element_by_id(profile, element_id)
        if element is not None:
            for ref in element.get("achievementRefs", []) or []:
                if not isinstance(ref, dict):
                    continue
                for achievement in self._sorted_achievements(profile):
                    if achievement.get("id") == ref.get("id") and achievement.get("statement"):
                        return str(achievement["statement"])
        return None

    def _org_name(self, profile: dict[str, Any], experience: dict[str, Any]) -> str | None:
        organizations = {
            org.get("id"): org.get("name")
            for org in profile.get("organizations", [])
            if org.get("id") and org.get("name")
        }
        for ref in experience.get("organizationRefs", []) or []:
            name = organizations.get(ref.get("id"))
            if name:
                return str(name)
        return None

    # ------------------------------------------------------------------
    # Deterministic lookups
    # ------------------------------------------------------------------

    @staticmethod
    def _sorted_experiences(profile: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            (exp for exp in profile.get("experiences", []) if exp.get("id")),
            key=lambda exp: exp.get("id", ""),
        )

    @staticmethod
    def _sorted_projects(profile: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            (proj for proj in profile.get("projects", []) if proj.get("id")),
            key=lambda proj: proj.get("id", ""),
        )

    @staticmethod
    def _sorted_achievements(profile: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            (ach for ach in profile.get("achievements", []) if ach.get("id")),
            key=lambda ach: ach.get("id", ""),
        )

    @staticmethod
    def _skills_by_id(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            skill.get("id"): skill
            for skill in profile.get("skills", [])
            if skill.get("id")
        }

    @staticmethod
    def _experiences_by_id(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            exp.get("id"): exp
            for exp in profile.get("experiences", [])
            if exp.get("id")
        }

    def _element_by_id(self, profile: dict[str, Any], element_id: str) -> dict[str, Any] | None:
        for collection in (
            "experiences",
            "projects",
            "skills",
            "achievements",
            "education",
            "certifications",
        ):
            for element in profile.get(collection, []):
                if element.get("id") == element_id:
                    return element
            return None


def build_preparation_plan(
    profile: dict[str, Any],
    *,
    target_role: str | None = None,
    target_contexts: Sequence[dict[str, Any]] = (),
    max_questions_per_category: int = 2,
) -> InterviewPlan:
    """Build the deterministic ``InterviewPlan`` backing a Preparation Guide.

    This is the single integration point that the generation pipeline calls
    when producing an Interview Preparation Guide artifact (M1.16). It derives
    the ``target_role`` and ``target_context_id`` from the artifact's resolved
    target contexts (first context wins) unless given explicitly, then
    delegates entirely to ``InterviewEngine.generate_plan`` so the plan stays
    deterministic and reuses Core (Knowledge Graph, concept taxonomy,
    requirement extraction).
    """
    role = target_role
    target_context_id: str | None = None
    for context in target_contexts or ():
        if role is None and context.get("role"):
            role = str(context["role"])
        if target_context_id is None and context.get("id"):
            target_context_id = str(context["id"])
        if role is not None and target_context_id is not None:
            break

    return InterviewEngine(
        max_questions_per_category=max_questions_per_category,
    ).generate_plan(
        profile,
        target_role=role,
        target_context_id=target_context_id,
    )
