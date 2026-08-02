"""Resolution Engine for CareerOS.

Applies deterministic, guided resolutions to a canonical profile dict in place.
Resolutions are the concrete edits a user authorizes when acting on a
recommendation (e.g. tagging a project with skills, appending technologies to an
experience, linking skill evidence, or persisting a measurable achievement).

This is a **Core** capability: it operates on the canonical profile and the
artifact lifecycle. Any module that lets a user act on profile findings (AI
Tailoring, Interview Preparation, Skill Gap Analysis, Application Tracking) can
reuse it without importing the delivery layer or any AI Tailoring code.

Design constraints:

- Resolutions are deterministic and schema-compliant edits.
- The canonical profile is the single source of truth.
- If a resolution mutates the profile, every generated artifact that exports the
  resolved element is marked ``stale``. Nothing is regenerated automatically:
  regeneration is an explicit user action.
- This module is free of HTTP / delivery-layer concepts. Transport errors are
  expressed as typed exceptions so any consumer can map them to its own error
  surface.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .exceptions import CareerOSException
from .measurability import is_measurable

RESOLVABLE_RULES: set[str] = {
    "ProjectWithoutSkillsRule",
    "ExperienceNoTechnologiesRule",
    "SkillWithoutExperienceRule",
    "NoMeasurableAchievementRule",
}

_ARTIFACT_STATUS_CURRENT = "current"
_ARTIFACT_STATUS_STALE = "stale"

# Maps each resolution rule to the profile element type it mutates. Used to
# derive which generated artifacts export the resolved element and must be
# marked stale.
_RESOLUTION_ELEMENT_TYPES: dict[str, str] = {
    "ProjectWithoutSkillsRule": "project",
    "ExperienceNoTechnologiesRule": "experience",
    "SkillWithoutExperienceRule": "skill",
    "NoMeasurableAchievementRule": "experience",
}


class ResolutionError(CareerOSException):
    """Base class for Resolution Engine failures."""


class UnsupportedRuleError(ResolutionError):
    """The requested rule is not supported by the Resolution Engine."""


class ResolutionTargetNotFoundError(ResolutionError):
    """The profile element targeted by a resolution does not exist."""


class InvalidAchievementError(ResolutionError):
    """A measurable achievement statement is required to resolve the rule."""


class AchievementNotMeasurableError(ResolutionError):
    """The supplied achievement statement does not look measurable."""


def _mark_affected_artifacts_stale(data: dict[str, Any], element_id: str, element_type: str) -> None:
    """Mark generated artifacts that export the resolved element as stale.

    An artifact is affected when one of its sourceRefs references the element the
    resolution mutated. The stale flag only records lifecycle state; nothing is
    regenerated here.
    """
    for artifact in data.get("artifacts", []):
        source_refs = artifact.get("sourceRefs", [])
        references_element = any(
            isinstance(r, dict)
            and r.get("id") == element_id
            and r.get("type") == element_type
            for r in source_refs
        )
        if references_element:
            artifact["status"] = _ARTIFACT_STATUS_STALE


def _resolve_element(data: dict[str, Any], rule: str, element_id: str) -> dict[str, Any]:
    """Locate the canonical element edited by a resolution rule."""
    key = {
        "ProjectWithoutSkillsRule": "projects",
        "ExperienceNoTechnologiesRule": "experiences",
        "SkillWithoutExperienceRule": "skills",
        "NoMeasurableAchievementRule": "experiences",
    }[rule]
    for element in data.get(key, []):
        if element.get("id") == element_id:
            return element
    raise ResolutionTargetNotFoundError(f"{rule} target not found: {element_id}")


def apply_resolution(
    data: dict[str, Any],
    *,
    triggered_rule: str,
    element_id: str,
    skill_ids: Sequence[str] | None = None,
    experience_ids: Sequence[str] | None = None,
    technologies: Sequence[str] | None = None,
    achievement_statement: str = "",
) -> None:
    """Apply a guided resolution to a canonical profile dict in place.

    If the resolution mutates the canonical profile, every generated artifact
    that exports the resolved element is marked stale. Artifacts are never
    regenerated automatically: regeneration is an explicit user action.

    Args:
        data: The canonical profile payload (mutated in place).
        triggered_rule: The rule class name that produced the recommendation.
        element_id: ID of the profile element the resolution targets.
        skill_ids: Selected skill references (project / skill evidence).
        experience_ids: Selected experience references (project / skill evidence).
        technologies: Technology tags to attach to an experience.
        achievement_statement: Measurable achievement statement (NoMeasurableAchievementRule).

    Raises:
        UnsupportedRuleError: If ``triggered_rule`` is not resolvable.
        ResolutionTargetNotFoundError: If the target element does not exist.
        InvalidAchievementError: If the achievement statement is empty.
        AchievementNotMeasurableError: If the achievement statement is not measurable.
    """
    if triggered_rule not in RESOLVABLE_RULES:
        raise UnsupportedRuleError(f"Resolution is not supported for rule: {triggered_rule}")

    skill_ids = list(skill_ids or [])
    experience_ids = list(experience_ids or [])
    technologies = list(technologies or [])

    before = copy.deepcopy(data)

    if triggered_rule == "ProjectWithoutSkillsRule":
        project = _resolve_element(data, triggered_rule, element_id)
        project["skillRefs"] = [
            {"id": sid, "type": "skill"} for sid in skill_ids if sid
        ]
        project["experienceRefs"] = [
            {"id": eid, "type": "experience"} for eid in experience_ids if eid
        ]
    elif triggered_rule == "ExperienceNoTechnologiesRule":
        experience = _resolve_element(data, triggered_rule, element_id)
        tags = [t.strip() for t in technologies if t and t.strip()]
        if skill_ids:
            skills_by_id = {s.get("id"): s for s in data.get("skills", [])}
            for sid in skill_ids:
                if not sid or sid not in skills_by_id:
                    continue
                name = str(skills_by_id[sid].get("name", "") or "").strip()
                if name and name not in tags:
                    tags.append(name)
        if tags:
            scope = str(experience.get("scope", "") or "").strip()
            suffix = f"Key technologies: {', '.join(tags)}."
            experience["scope"] = f"{scope}\n{suffix}" if scope else suffix
    elif triggered_rule == "SkillWithoutExperienceRule":
        skill = _resolve_element(data, triggered_rule, element_id)
        extensions = skill.setdefault("extensions", {})
        evidence = extensions.setdefault("experienceEvidence", [])
        existing = {
            ev.get("experienceId") for ev in evidence if isinstance(ev, dict) and ev.get("experienceId")
        }
        for eid in experience_ids:
            if eid and eid not in existing:
                evidence.append({"experienceId": eid, "type": "experience"})
                existing.add(eid)
    elif triggered_rule == "NoMeasurableAchievementRule":
        experience = _resolve_element(data, triggered_rule, element_id)
        statement = (achievement_statement or "").strip()
        if not statement:
            raise InvalidAchievementError(
                "A measurable achievement statement is required to resolve this recommendation."
            )
        if not is_measurable(statement):
            raise AchievementNotMeasurableError(
                "The achievement statement does not look measurable. Add a metric, "
                "percentage, or business outcome (e.g. 'Reduced deployment time by 60%')."
            )

        achievements = data.setdefault("achievements", [])
        existing_ids = {
            a.get("id") for a in achievements if isinstance(a, dict) and a.get("id")
        }
        base_id = f"achievement-{element_id}"
        achievement_id = base_id
        counter = 1
        while achievement_id in existing_ids:
            counter += 1
            achievement_id = f"{base_id}-{counter}"

        achievement: dict[str, Any] = {
            "id": achievement_id,
            "statement": statement,
            "contextRefs": [{"id": element_id, "type": "experience"}],
        }
        selected_skills = [sid for sid in skill_ids if sid]
        if selected_skills:
            achievement["skillRefs"] = [
                {"id": sid, "type": "skill"} for sid in selected_skills
            ]
        achievements.append(achievement)

        refs = experience.setdefault("achievementRefs", [])
        if not any(
            isinstance(r, dict) and r.get("id") == achievement_id for r in refs
        ):
            refs.append({"id": achievement_id, "type": "achievement"})

        # Wire the new achievement into the artifact export pipeline: any artifact
        # that already exports the experience now also exports the achievement,
        # using the existing sourceRef mechanism. No second representation is created.
        achievement_source_ref: dict[str, Any] = {"id": achievement_id, "type": "achievement"}
        for artifact in data.get("artifacts", []):
            source_refs = artifact.get("sourceRefs", [])
            references_experience = any(
                isinstance(r, dict) and r.get("id") == element_id and r.get("type") == "experience"
                for r in source_refs
            )
            if not references_experience:
                continue
            if not any(
                isinstance(r, dict) and r.get("id") == achievement_id and r.get("type") == "achievement"
                for r in source_refs
            ):
                source_refs.append(achievement_source_ref)

    if data != before:
        _mark_affected_artifacts_stale(
            data,
            element_id,
            _RESOLUTION_ELEMENT_TYPES[triggered_rule],
        )
