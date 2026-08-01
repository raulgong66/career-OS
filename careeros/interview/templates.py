"""Interview Intelligence — deterministic question templates.

``QuestionTemplate`` is the analog of ``ArtifactTemplate`` for questions: a
parameterized prompt with named placeholders bound to canonical profile
elements at generation time. Templates hold no profile data; the engine decides
which templates fire based on profile evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import QuestionType


@dataclass(frozen=True)
class QuestionTemplate:
    """A parameterized, deterministic question generator.

    ``prompt_pattern`` may contain ``{placeholders}`` (e.g. ``{skill}``,
    ``{experience}``, ``{project}``, ``{role}``, ``{headline}``) that are
    substituted with verbatim profile excerpts by ``QuestionBuilder``.
    ``required_ref_types`` documents the canonical element types the template
    needs for evidence — used by tests and future tooling, not by the engine.
    """

    template_id: str
    category: QuestionType
    difficulty: str
    prompt_pattern: str
    description: str
    required_ref_types: tuple[str, ...] = ()


QUESTION_TEMPLATES: tuple[QuestionTemplate, ...] = (
    # --- Technical ---------------------------------------------------------
    QuestionTemplate(
        template_id="technical-skill-in-practice",
        category=QuestionType.TECHNICAL,
        difficulty="intermediate",
        prompt_pattern=(
            "Describe a time you used {skill} in {experience}. "
            "What problem were you solving, what approach did you take, "
            "and what was the outcome?"
        ),
        description="Technical deep-dive on a skill anchored to a real experience.",
        required_ref_types=("skill", "experience"),
    ),
    QuestionTemplate(
        template_id="technical-skill-decision",
        category=QuestionType.TECHNICAL,
        difficulty="advanced",
        prompt_pattern=(
            "Walk me through a technical decision you made around {skill}. "
            "How did you weigh the options and what trade-offs did you accept?"
        ),
        description="Technical decision-making around a skill.",
        required_ref_types=("skill", "experience"),
    ),
    # --- Behavioral --------------------------------------------------------
    QuestionTemplate(
        template_id="behavioral-experience-approach",
        category=QuestionType.BEHAVIORAL,
        difficulty="intermediate",
        prompt_pattern=(
            "Walk me through your work on {experience}. "
            "What was your role, how did you approach it, and what did you achieve?"
        ),
        description="Behavioral question anchored to an experience.",
        required_ref_types=("experience",),
    ),
    QuestionTemplate(
        template_id="behavioral-experience-outcome",
        category=QuestionType.BEHAVIORAL,
        difficulty="intermediate",
        prompt_pattern=(
            "Tell me about a difficult or ambiguous situation in {experience} "
            "and how you handled it."
        ),
        description="Behavioral question on handling difficulty.",
        required_ref_types=("experience",),
    ),
    # --- Leadership --------------------------------------------------------
    QuestionTemplate(
        template_id="leadership-experience",
        category=QuestionType.LEADERSHIP,
        difficulty="advanced",
        prompt_pattern=(
            "Describe a situation from {experience} where you took a leadership role. "
            "What did you own, how did you drive the outcome, and what was the result?"
        ),
        description="Leadership question anchored to a leadership-signalled experience.",
        required_ref_types=("experience",),
    ),
    # --- Project deep dive -------------------------------------------------
    QuestionTemplate(
        template_id="project-deep-dive",
        category=QuestionType.PROJECT_DEEP_DIVE,
        difficulty="advanced",
        prompt_pattern=(
            "Walk me through the {project} project end to end: "
            "the problem it solved, your role, the architecture you chose, "
            "and the measurable outcome."
        ),
        description="End-to-end deep dive on a canonical project.",
        required_ref_types=("project",),
    ),
    QuestionTemplate(
        template_id="project-role-contribution",
        category=QuestionType.PROJECT_DEEP_DIVE,
        difficulty="intermediate",
        prompt_pattern=(
            "What was your specific contribution to {project}, "
            "and how did you validate that it worked?"
        ),
        description="Ownership and validation of a project.",
        required_ref_types=("project",),
    ),
    # --- Problem solving ---------------------------------------------------
    QuestionTemplate(
        template_id="problem-solving-experience",
        category=QuestionType.PROBLEM_SOLVING,
        difficulty="intermediate",
        prompt_pattern=(
            "Describe the most complex problem you solved in {experience}. "
            "How did you diagnose it, what were the constraints, and what was the result?"
        ),
        description="Problem-solving question anchored to an experience.",
        required_ref_types=("experience",),
    ),
    QuestionTemplate(
        template_id="problem-solving-operations",
        category=QuestionType.PROBLEM_SOLVING,
        difficulty="intermediate",
        prompt_pattern=(
            "Tell me about a time you resolved a critical incident or issue in {experience}. "
            "What was the impact on availability, cost, or the business?"
        ),
        description="Operational incident resolution.",
        required_ref_types=("experience",),
    ),
    # --- Career motivation -------------------------------------------------
    QuestionTemplate(
        template_id="career-motivation-target",
        category=QuestionType.CAREER_MOTIVATION,
        difficulty="basic",
        prompt_pattern=(
            "You're interested in a {role} role. What in your career — for example "
            "{experience} — has prepared you for it, and what motivates you to keep "
            "moving in this direction?"
        ),
        description="Career motivation question with an experience anchor.",
        required_ref_types=("person", "experience"),
    ),
    QuestionTemplate(
        template_id="career-motivation-direction",
        category=QuestionType.CAREER_MOTIVATION,
        difficulty="basic",
        prompt_pattern=(
            "Your profile highlights {headline}. Why this direction, "
            "and where do you want to grow over the next few years?"
        ),
        description="Career motivation question from positioning.",
        required_ref_types=("person",),
    ),
)


def template_for(template_id: str) -> QuestionTemplate | None:
    """Look up a template by id (case-sensitive)."""
    for template in QUESTION_TEMPLATES:
        if template.template_id == template_id:
            return template
    return None


def templates_for(category: QuestionType) -> tuple[QuestionTemplate, ...]:
    """Return registered templates for a category in registration order."""
    return tuple(
        template
        for template in QUESTION_TEMPLATES
        if template.category == category
    )
