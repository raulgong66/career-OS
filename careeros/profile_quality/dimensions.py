"""Eight pure profile health dimension calculators (M1.24 Spec SS3.4).

Every function is a **pure function on a canonical profile dict**: it reads the
profile, computes a score in ``[0.0, 1.0]``, and returns the dimension findings
and citations for the elements that fail its criterion. No AI, no randomness,
no external state, no knowledge graph, no rule execution (AC 1.11).

These calculators aggregate concepts that already exist in
``careeros.reasoning.rules.recommendation_rules`` (reusing predicates such as
``_is_measurable``, ``TECHNOLOGY_KEYWORDS``, ``_normalize_skill_name``, and
``word_boundary_match``). They introduce **no new business rules** (M1.24.0
clarification): each score is a ratio over profile elements and every finding
references the corresponding rule id.
"""

from __future__ import annotations

from typing import Any, Callable

from careeros.reasoning.rules.recommendation_rules import (
    _is_measurable,
    _normalize_skill_name,
    GENERIC_SUMMARY_WORDS,
    TECHNOLOGY_KEYWORDS,
)
from careeros.reasoning.utils import word_boundary_match

from .report import (
    Citation,
    Finding,
    HealthDimension,
    RULE_ID_TO_DIMENSION,
    resolution_type_for_rule,
)

DIMENSION_WEIGHTS: dict[str, float] = {
    "achievement_measurability": 0.20,
    "skill_evidence_coverage": 0.20,
    "technology_presence": 0.15,
    "summary_quality": 0.10,
    "skill_deduplication": 0.10,
    "business_outcome_language": 0.10,
    "certification_utilization": 0.10,
    "project_skill_linkage": 0.05,
}

HEALTH_DIMENSIONS: tuple[str, ...] = tuple(DIMENSION_WEIGHTS.keys())

DIMENSION_LABELS: dict[str, str] = {
    "achievement_measurability": "Achievement Measurability",
    "skill_evidence_coverage": "Skill Evidence Coverage",
    "technology_presence": "Technology Presence",
    "summary_quality": "Summary Quality",
    "skill_deduplication": "Skill Deduplication",
    "business_outcome_language": "Business Outcome Language",
    "certification_utilization": "Certification Utilization",
    "project_skill_linkage": "Project Skill Linkage",
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "achievement_measurability": (
        "% of experiences with at least one measurable achievement"
    ),
    "skill_evidence_coverage": (
        "% of skills with at least one experience or achievement evidence link"
    ),
    "technology_presence": (
        "% of experiences mentioning at least one recognized technology"
    ),
    "summary_quality": (
        "1 if a professional summary exists, is non-generic, >= 40 chars, and "
        "has metrics or technologies; else 0"
    ),
    "skill_deduplication": (
        "1 - (duplicate_count / total_skills) after name normalization"
    ),
    "business_outcome_language": (
        "% of achievements with business outcome words"
    ),
    "certification_utilization": (
        "% of certifications referenced in experience or with evidence"
    ),
    "project_skill_linkage": (
        "% of projects with at least one skillRef or experienceRef"
    ),
}

_PROFILE_ELEMENT = "profile"


def health_dimensions() -> tuple[HealthDimension, ...]:
    """Return descriptor objects for the eight health dimensions."""
    return tuple(
        HealthDimension(
            name=name,
            weight=DIMENSION_WEIGHTS[name],
            label=DIMENSION_LABELS[name],
            description=DIMENSION_DESCRIPTIONS[name],
        )
        for name in HEALTH_DIMENSIONS
    )


def _build_finding(
    rule_id: str,
    *,
    element_id: str,
    element_type: str,
    title: str,
    reason: str,
    suggested_action: str,
    priority: str,
    estimated_impact: str,
    confidence: str,
    citation: Citation,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        dimension=RULE_ID_TO_DIMENSION[rule_id],
        element_id=element_id,
        element_type=element_type,
        title=title,
        reason=reason,
        suggested_action=suggested_action,
        resolution_type=resolution_type_for_rule(rule_id),
        evidence_refs=(),
        priority=priority,
        estimated_impact=estimated_impact,
        confidence=confidence,
        citations=(citation,),
    )


def _citations_of(findings: list[Finding]) -> list[Citation]:
    return [c for finding in findings for c in finding.citations]


def _searchable_text(profile: dict[str, Any]) -> str:
    """Deterministic search text over experiences and achievements."""
    parts: list[str] = []
    for exp in profile.get("experiences", []):
        if isinstance(exp, dict):
            parts.append(
                f"{exp.get('title', '') or ''} {exp.get('scope', '') or ''}"
            )
    for achievement in profile.get("achievements", []):
        if isinstance(achievement, dict):
            parts.append(
                f"{achievement.get('title', '') or ''} "
                f"{achievement.get('description', '') or ''}"
            )
    return " ".join(parts).lower()


def _person_id(profile: dict[str, Any]) -> str:
    person = profile.get("person", {})
    if isinstance(person, dict):
        return str(person.get("id", "") or "") or _PROFILE_ELEMENT
    return _PROFILE_ELEMENT


# ---------------------------------------------------------------------------
# 1. Achievement Measurability
# ---------------------------------------------------------------------------


def calculate_achievement_measurability(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of experiences with >= 1 measurable achievement."""
    experiences = profile.get("experiences", [])
    if not experiences:
        return 1.0, [], []

    achievements_by_id = {
        a.get("id"): a
        for a in profile.get("achievements", [])
        if isinstance(a, dict)
    }
    findings: list[Finding] = []
    good = 0
    for index, exp in enumerate(experiences):
        if not isinstance(exp, dict):
            continue
        ref_ids = [
            ref.get("id")
            for ref in exp.get("achievementRefs", [])
            if isinstance(ref, dict)
        ]
        measurable = any(
            _is_measurable(achievements_by_id.get(ref_id))
            for ref_id in ref_ids
            if ref_id in achievements_by_id
        )
        if measurable:
            good += 1
            continue
        title = str(exp.get("title", "") or "").strip() or "this role"
        element_id = str(exp.get("id", "") or "") or f"experience:{index}"
        citation = Citation(
            entity_id=element_id,
            entity_type="experience",
            property_path="achievementRefs",
            snippet=title,
        )
        findings.append(
            _build_finding(
                "recommendation_add_measurable_achievement",
                element_id=element_id,
                element_type="experience",
                title="Add measurable achievements",
                reason=(
                    f"'{title}' has no measurable achievement attached — it "
                    "describes responsibilities without evidence of results."
                ),
                suggested_action=(
                    "Add a quantified outcome (e.g. 'Reduced deployment time by 60%')."
                ),
                priority="high",
                estimated_impact="high",
                confidence="high",
                citation=citation,
            )
        )

    score = good / len(experiences)
    return score, findings, _citations_of(findings)


# ---------------------------------------------------------------------------
# 2. Skill Evidence Coverage
# ---------------------------------------------------------------------------


def calculate_skill_evidence_coverage(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of skills with at least one experience/achievement evidence link."""
    skills = profile.get("skills", [])
    if not skills:
        return 1.0, [], []

    searchable = _searchable_text(profile)
    findings: list[Finding] = []
    good = 0
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            continue
        name = str(skill.get("name", "") or "").strip()
        if not name:
            continue
        experience_evidence = bool(
            skill.get("extensions", {}).get("experienceEvidence")
        )
        evidenced = experience_evidence or word_boundary_match(
            name.lower(), searchable
        )
        if evidenced:
            good += 1
            continue
        element_id = str(skill.get("id", "") or "") or f"skill:{index}"
        category = str(skill.get("category", "") or "")
        citation = Citation(
            entity_id=element_id,
            entity_type="skill",
            property_path="extensions.experienceEvidence",
            snippet=name,
        )
        findings.append(
            _build_finding(
                "recommendation_show_skill_in_experience",
                element_id=element_id,
                element_type="skill",
                title="Show how you use this skill",
                reason=(
                    f"'{name}' is listed as a skill but never appears in your "
                    "experience or achievements."
                ),
                suggested_action=(
                    f"Add a concrete example that shows how you use {name} to an "
                    "experience or achievement."
                ),
                priority="high" if category else "medium",
                estimated_impact="medium",
                confidence="high" if category else "medium",
                citation=citation,
            )
        )

    score = good / len(skills)
    return score, findings, _citations_of(findings)


# ---------------------------------------------------------------------------
# 3. Technology Presence
# ---------------------------------------------------------------------------


def calculate_technology_presence(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of experiences mentioning at least one technology keyword."""
    experiences = profile.get("experiences", [])
    if not experiences:
        return 1.0, [], []

    findings: list[Finding] = []
    good = 0
    for index, exp in enumerate(experiences):
        if not isinstance(exp, dict):
            continue
        combined = (
            f"{exp.get('title', '') or ''} {exp.get('scope', '') or ''}"
        ).lower()
        has_technology = any(
            word_boundary_match(keyword, combined)
            for keyword in TECHNOLOGY_KEYWORDS
        )
        if has_technology:
            good += 1
            continue
        title = str(exp.get("title", "") or "").strip() or "this role"
        scope = str(exp.get("scope", "") or "").strip()
        element_id = str(exp.get("id", "") or "") or f"experience:{index}"
        if not scope:
            reason = (
                f"'{title}' has no description at all — nothing tells a reviewer "
                "what you did or what you used."
            )
            priority = "high"
            confidence = "high"
        else:
            reason = (
                f"'{title}' describes work without naming any specific tool or "
                "technology."
            )
            priority = "medium"
            confidence = "medium"
        citation = Citation(
            entity_id=element_id,
            entity_type="experience",
            property_path="scope",
            snippet=title,
        )
        findings.append(
            _build_finding(
                "recommendation_add_technologies",
                element_id=element_id,
                element_type="experience",
                title="Name the technologies you used",
                reason=reason,
                suggested_action=(
                    "Describe your responsibilities and name the tools and "
                    "technologies you used (e.g., Python, AWS, Kubernetes)."
                ),
                priority=priority,
                estimated_impact="high",
                confidence=confidence,
                citation=citation,
            )
        )

    score = good / len(experiences)
    return score, findings, _citations_of(findings)


# ---------------------------------------------------------------------------
# 4. Summary Quality
# ---------------------------------------------------------------------------


def calculate_summary_quality(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: 1.0 for a strong summary, else 0.0 (binary dimension)."""
    summaries = profile.get("professionalSummaries", [])
    texts = [
        str(s.get("text", "") or "").strip()
        for s in summaries
        if isinstance(s, dict)
    ]
    texts = [text for text in texts if text]
    combined = " ".join(texts).lower()

    if not texts:
        return _summary_finding(profile, "missing", texts)

    has_number = any(char.isdigit() for char in combined)
    has_technology = any(
        word_boundary_match(keyword, combined)
        for keyword in TECHNOLOGY_KEYWORDS
    )
    generic_hits = sum(
        1
        for word in GENERIC_SUMMARY_WORDS
        if word_boundary_match(word, combined)
    )
    too_short = len(combined) < 40

    if not too_short and (has_number or has_technology) and generic_hits < 2:
        return 1.0, [], []

    return _summary_finding(profile, "generic" if not too_short else "short", texts)


def _summary_finding(
    profile: dict[str, Any],
    kind: str,
    texts: list[str],
) -> tuple[float, list[Finding], list[Citation]]:
    element_id = _person_id(profile)
    citation = Citation(
        entity_id=element_id,
        entity_type="profile",
        property_path="professionalSummaries",
        snippet=texts[0][:200] if texts else "",
    )
    if kind == "missing":
        finding = _build_finding(
            "recommendation_improve_summary",
            element_id=element_id,
            element_type="profile",
            title="Add a professional summary",
            reason="Your profile has no professional summary.",
            suggested_action=(
                "Write 2-3 lines covering your role, your strongest skills, and "
                "one quantified highlight."
            ),
            priority="high",
            estimated_impact="high",
            confidence="high",
            citation=citation,
        )
    else:
        finding = _build_finding(
            "recommendation_improve_summary",
            element_id=element_id,
            element_type="profile",
            title="Strengthen your professional summary",
            reason="Your professional summary reads as generic.",
            suggested_action=(
                "Lead with your specialty, name key technologies, and include a "
                "quantified result."
            ),
            priority="medium",
            estimated_impact="medium",
            confidence="medium",
            citation=citation,
        )
    return 0.0, [finding], [citation]


# ---------------------------------------------------------------------------
# 5. Skill Deduplication
# ---------------------------------------------------------------------------


def calculate_skill_deduplication(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: 1 - (duplicate_count / total_skills) after normalization."""
    skills = profile.get("skills", [])
    names = [
        str(skill.get("name", "") or "").strip()
        for skill in skills
        if isinstance(skill, dict)
    ]
    names = [name for name in names if name]
    if not names:
        return 1.0, [], []

    normalized: dict[str, list[str]] = {}
    for name in names:
        key = _normalize_skill_name(name)
        if key:
            normalized.setdefault(key, []).append(name)

    duplicate_count = sum(len(values) - 1 for values in normalized.values())
    if duplicate_count == 0:
        return 1.0, [], []

    score = 1 - (duplicate_count / len(names))
    duplicate_names = sorted(
        {name for values in normalized.values() if len(values) > 1 for name in values}
    )
    element_id = _person_id(profile)
    quoted = ", ".join(f"'{name}'" for name in duplicate_names)
    citation = Citation(
        entity_id=element_id,
        entity_type="profile",
        property_path="skills",
        snippet=", ".join(duplicate_names),
    )
    finding = _build_finding(
        "recommendation_remove_duplicate_skills",
        element_id=element_id,
        element_type="profile",
        title="Merge duplicate skills",
        reason=f"{quoted} appear to be the same skill.",
        suggested_action=(
            "Merge them into one skill entry and keep the strongest evidence for it."
        ),
        priority="low",
        estimated_impact="low",
        confidence="medium",
        citation=citation,
    )
    return score, [finding], [citation]


# ---------------------------------------------------------------------------
# 6. Business Outcome Language
# ---------------------------------------------------------------------------


def calculate_business_outcome_language(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of achievements with a measurable business outcome."""
    achievements = profile.get("achievements", [])
    if not achievements:
        return 1.0, [], []

    findings: list[Finding] = []
    good = 0
    for index, achievement in enumerate(achievements):
        if not isinstance(achievement, dict):
            continue
        if _is_measurable(achievement):
            good += 1
            continue
        title = (
            str(achievement.get("title", "") or "").strip()
            or str(achievement.get("statement", "") or "").strip()[:120]
            or "this achievement"
        )
        element_id = (
            str(achievement.get("id", "") or "") or f"achievement:{index}"
        )
        citation = Citation(
            entity_id=element_id,
            entity_type="achievement",
            property_path="achievements",
            snippet=title,
        )
        findings.append(
            _build_finding(
                "recommendation_add_business_outcome",
                element_id=element_id,
                element_type="achievement",
                title="Add a measurable business outcome",
                reason=(
                    f"'{title}' describes activity but not a result — reviewers "
                    "cannot see the value it delivered."
                ),
                suggested_action=(
                    "State the outcome of this achievement and quantify it where "
                    "possible."
                ),
                priority="medium",
                estimated_impact="high",
                confidence="medium",
                citation=citation,
            )
        )

    score = good / len(achievements)
    return score, findings, _citations_of(findings)


# ---------------------------------------------------------------------------
# 7. Certification Utilization
# ---------------------------------------------------------------------------


def calculate_certification_utilization(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of certifications referenced in experience or with evidence."""
    certifications = profile.get("certifications", [])
    if not certifications:
        return 1.0, [], []

    searchable = _searchable_text(profile)
    findings: list[Finding] = []
    good = 0
    for index, certification in enumerate(certifications):
        if not isinstance(certification, dict):
            continue
        name = str(certification.get("name", "") or "").strip()
        if not name:
            continue
        evidenced = bool(certification.get("evidenceRefs")) or word_boundary_match(
            name.lower(), searchable
        )
        if evidenced:
            good += 1
            continue
        element_id = (
            str(certification.get("id", "") or "") or f"certification:{index}"
        )
        citation = Citation(
            entity_id=element_id,
            entity_type="certification",
            property_path="certifications",
            snippet=name,
        )
        findings.append(
            _build_finding(
                "recommendation_show_certification_value",
                element_id=element_id,
                element_type="certification",
                title="Show the value of this certification",
                reason=(
                    f"'{name}' is listed but never connected to your experience "
                    "or achievements."
                ),
                suggested_action=(
                    "Mention where you applied this certification, or reference it "
                    "in a relevant achievement."
                ),
                priority="medium",
                estimated_impact="medium",
                confidence="medium",
                citation=citation,
            )
        )

    score = good / len(certifications)
    return score, findings, _citations_of(findings)


# ---------------------------------------------------------------------------
# 8. Project Skill Linkage
# ---------------------------------------------------------------------------


def calculate_project_skill_linkage(
    profile: dict[str, Any],
) -> tuple[float, list[Finding], list[Citation]]:
    """Score: % of projects with at least one skillRef or experienceRef."""
    projects = profile.get("projects", [])
    if not projects:
        return 1.0, [], []

    findings: list[Finding] = []
    good = 0
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            continue
        if project.get("skillRefs") or project.get("experienceRefs"):
            good += 1
            continue
        title = str(project.get("title", "") or "").strip() or "This project"
        element_id = str(project.get("id", "") or "") or f"project:{index}"
        citation = Citation(
            entity_id=element_id,
            entity_type="project",
            property_path="projects",
            snippet=title,
        )
        findings.append(
            _build_finding(
                "recommendation_add_skills_to_project",
                element_id=element_id,
                element_type="project",
                title="Tag this project with skills",
                reason=f"'{title}' is not linked to any skills or experiences.",
                suggested_action=(
                    "Tag the project with the skills it demonstrates, or link it "
                    "to a related experience."
                ),
                priority="low",
                estimated_impact="medium",
                confidence="low",
                citation=citation,
            )
        )

    score = good / len(projects)
    return score, findings, _citations_of(findings)


DimensionCalculator = Callable[[dict[str, Any]], tuple[float, list[Finding], list[Citation]]]

DIMENSION_CALCULATORS: dict[str, DimensionCalculator] = {
    "achievement_measurability": calculate_achievement_measurability,
    "skill_evidence_coverage": calculate_skill_evidence_coverage,
    "technology_presence": calculate_technology_presence,
    "summary_quality": calculate_summary_quality,
    "skill_deduplication": calculate_skill_deduplication,
    "business_outcome_language": calculate_business_outcome_language,
    "certification_utilization": calculate_certification_utilization,
    "project_skill_linkage": calculate_project_skill_linkage,
}

__all__ = [
    "DIMENSION_CALCULATORS",
    "DIMENSION_DESCRIPTIONS",
    "DIMENSION_LABELS",
    "DIMENSION_WEIGHTS",
    "HEALTH_DIMENSIONS",
    "calculate_achievement_measurability",
    "calculate_business_outcome_language",
    "calculate_certification_utilization",
    "calculate_project_skill_linkage",
    "calculate_skill_deduplication",
    "calculate_skill_evidence_coverage",
    "calculate_summary_quality",
    "calculate_technology_presence",
    "health_dimensions",
]
