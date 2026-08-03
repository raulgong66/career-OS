from __future__ import annotations

from datetime import datetime
from typing import Any

from careeros.reasoning import ReasoningResult, Rule, RuleContext
from careeros.reasoning.utils import (
    detect_cloud_provider,
    detect_industry,
    detect_leadership_role,
    detect_responsibility_areas,
    duration_between,
    duration_years,
    format_duration,
    has_migration_keywords,
    parse_date_range,
    reference_now,
    title_level,
    total_experience_years,
)


def _org_name_and_id(
    exp: dict[str, Any],
    context: RuleContext,
) -> tuple[str, str | None]:
    org_refs = exp.get("organizationRefs")
    if org_refs and len(org_refs) > 0:
        org_id = org_refs[0].get("id")
        org_node = context.graph.nodes.get(org_id) if org_id else None
        org_name = org_node.label if org_node else (org_id or "Unknown Organization")
        return org_name, org_id
    return "Unknown Organization", None


def _build_exp_skills_map(profile: dict[str, Any]) -> dict[str, list[str]]:
    exp_skills: dict[str, list[str]] = {}
    for skill in profile.get("skills", []):
        skill_name = skill.get("name", "")
        evidence = skill.get("extensions", {}).get("experienceEvidence", [])
        for ev in evidence:
            exp_id = ev.get("experienceId")
            if exp_id:
                exp_skills.setdefault(exp_id, []).append(skill_name)
    return exp_skills


# ---------------------------------------------------------------------------
# 1. StrongestExperienceRule
# ---------------------------------------------------------------------------


class StrongestExperienceRule(Rule):
    id = "strongest_experience"
    name = "Strongest Experience"
    description = "Ranks professional experiences by duration, seniority, responsibilities, and leadership indicators"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        ranked = self._rank_experiences(experiences, context)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="strongest_experience",
                value=ranked,
                confidence=1.0,
                evidence_refs=tuple(
                    e.get("id", "") for e in experiences if e.get("id")
                ),
                metadata={
                    "total_experiences": len(experiences),
                    "top_score": round(ranked[0]["score"], 4) if ranked else 0.0,
                    "top_experience_id": ranked[0]["experience_id"] if ranked else "",
                },
            )
        ]

    @staticmethod
    def _rank_experiences(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for exp in experiences:
            dr = parse_date_range(exp.get("dateRange"))
            dur = duration_years(dr)
            title = exp.get("title", "")
            tl = title_level(title)
            has_scope = bool(exp.get("scope"))
            has_leadership = detect_leadership_role(title) is not None
            org_name, _ = _org_name_and_id(exp, context)

            duration_score = min(dur / 10.0, 1.0) * 0.30
            seniority_score = (tl / 5.0) * 0.25
            responsibility_score = 0.20 if has_scope else 0.0
            leadership_score = 0.25 if has_leadership else 0.0
            total_score = duration_score + seniority_score + responsibility_score + leadership_score

            scored.append(
                {
                    "experience_id": exp.get("id", ""),
                    "title": title,
                    "organization": org_name,
                    "score": round(total_score, 4),
                    "duration_years": round(dur, 2),
                    "title_level": tl,
                    "has_scope": has_scope,
                    "has_leadership": has_leadership,
                }
            )

        scored.sort(key=lambda x: (-x["score"], -x["duration_years"], x["title"]))
        return scored


# ---------------------------------------------------------------------------
# 2. LeadershipExperienceRule
# ---------------------------------------------------------------------------


class LeadershipExperienceRule(Rule):
    id = "leadership_experience"
    name = "Leadership Experience"
    description = "Identifies leadership evidence from professional experiences"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        roles: list[dict[str, Any]] = []
        has_leadership = False
        refs: list[str] = []

        for exp in experiences:
            title = exp.get("title", "")
            role = detect_leadership_role(title)
            if role:
                has_leadership = True
                org_name, _ = _org_name_and_id(exp, context)
                roles.append(
                    {
                        "experience_id": exp.get("id", ""),
                        "title": title,
                        "role": role,
                        "organization": org_name,
                    }
                )
                refs.append(exp.get("id", ""))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="leadership_experience",
                value={
                    "has_leadership": has_leadership,
                    "leadership_roles": roles,
                },
                confidence=1.0,
                evidence_refs=tuple(refs),
                metadata={
                    "total_leadership_roles": len(roles),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 3. CloudExperienceRule
# ---------------------------------------------------------------------------


class CloudExperienceRule(Rule):
    id = "cloud_experience"
    name = "Cloud Experience"
    description = "Measures cloud platform experience across AWS, Azure, and GCP"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skills = context.profile.get("skills", [])
        experiences = context.profile.get("experiences", [])

        provider_data: dict[str, Any] = {
            "AWS": {"detected": False},
            "Azure": {"detected": False},
            "GCP": {"detected": False},
        }
        ref_set: set[str] = set()

        for skill in skills:
            skill_name = skill.get("name", "")
            provider = detect_cloud_provider(skill_name)
            if provider is None:
                continue

            data = provider_data[provider]
            if not data["detected"]:
                data["detected"] = True
                data["skills"] = []
                data["frequency"] = 0
                data["experience_ids"] = []

            data["skills"].append(skill_name)
            data["frequency"] += 1

            evidence = skill.get("extensions", {}).get("experienceEvidence", [])
            for ev in evidence:
                exp_id = ev.get("experienceId")
                if exp_id:
                    if exp_id not in data["experience_ids"]:
                        data["experience_ids"].append(exp_id)
                    ref_set.add(exp_id)

        for provider, data in provider_data.items():
            if not data.get("detected"):
                continue
            exp_ids = data.get("experience_ids", [])
            first: datetime | None = None
            most_recent: datetime | None = None
            for exp in experiences:
                if exp.get("id") in exp_ids:
                    dr = parse_date_range(exp.get("dateRange"))
                    if dr.start and (first is None or dr.start < first):
                        first = dr.start
                    end = dr.end if dr.end is not None else reference_now()
                    if most_recent is None or end > most_recent:
                        most_recent = end
            data["first_use"] = first.strftime("%Y-%m") if first else None
            data["most_recent_use"] = most_recent.strftime("%Y-%m") if most_recent else None
            data["estimated_years"] = (
                round(duration_between(first, most_recent), 1)
                if first and most_recent
                else None
            )

        has_cloud = any(d.get("detected") for d in provider_data.values())

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="cloud_experience",
                value={
                    "providers": provider_data,
                    "has_cloud_experience": has_cloud,
                },
                confidence=1.0,
                evidence_refs=tuple(sorted(ref_set)),
                metadata={
                    "providers_detected": [
                        p for p, d in provider_data.items() if d.get("detected")
                    ],
                },
            )
        ]


# ---------------------------------------------------------------------------
# 4. TechnologyBreadthRule
# ---------------------------------------------------------------------------


class TechnologyBreadthRule(Rule):
    id = "technology_breadth"
    name = "Technology Breadth"
    description = "Calculates total unique technologies grouped by category"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skills = context.profile.get("skills", [])

        categories: dict[str, list[dict[str, Any]]] = {}
        for skill in skills:
            raw_cat = skill.get("category") or ""
            cat = raw_cat if raw_cat.strip() else "Uncategorized"
            categories.setdefault(cat, []).append(
                {"id": skill.get("id", ""), "name": skill.get("name", "")}
            )

        total = len(skills)
        cat_counts = {
            cat: {"count": len(items), "skills": [s["name"] for s in items]}
            for cat, items in categories.items()
        }

        strongest: str | None = None
        weakest: str | None = None
        if cat_counts:
            strongest = max(cat_counts, key=lambda c: cat_counts[c]["count"])
            weakest = min(cat_counts, key=lambda c: cat_counts[c]["count"])

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="technology_breadth",
                value={
                    "total_technologies": total,
                    "categories": cat_counts,
                    "strongest_category": strongest,
                    "weakest_category": weakest,
                },
                confidence=1.0,
                evidence_refs=tuple(
                    s.get("id", "") for s in skills if s.get("id")
                ),
                metadata={
                    "category_count": len(categories),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 5. DomainExperienceRule
# ---------------------------------------------------------------------------


class DomainExperienceRule(Rule):
    id = "domain_experience"
    name = "Domain Experience"
    description = "Determines industries worked in based on organization names, titles, and scope"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])

        domains: dict[str, dict[str, Any]] = {}
        domain_exp_map: dict[str, set[str]] = {}
        domain_orgs: dict[str, set[str]] = {}

        for exp in experiences:
            title = exp.get("title", "")
            scope = exp.get("scope", "")
            org_name, _ = _org_name_and_id(exp, context)
            industry = detect_industry(org_name, title=title, scope=scope)
            if industry is None:
                continue

            dr = parse_date_range(exp.get("dateRange"))
            dur = duration_years(dr)
            exp_id = exp.get("id", "")

            domain_exp_map.setdefault(industry, set()).add(exp_id)
            domain_orgs.setdefault(industry, set()).add(org_name)

            if industry not in domains:
                domains[industry] = {
                    "years": 0.0,
                    "organization_count": 0,
                    "organizations": [],
                }
            domains[industry]["years"] += dur

        for industry in domains:
            domains[industry]["years"] = round(domains[industry]["years"], 1)
            orgs_sorted = sorted(domain_orgs.get(industry, set()))
            domains[industry]["organizations"] = orgs_sorted
            domains[industry]["organization_count"] = len(orgs_sorted)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="domain_experience",
                value=domains,
                confidence=1.0,
                evidence_refs=tuple(
                    e.get("id", "") for e in experiences if e.get("id")
                ),
                metadata={
                    "total_domains": len(domains),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 6. SeniorResponsibilityRule
# ---------------------------------------------------------------------------


class SeniorResponsibilityRule(Rule):
    id = "senior_responsibility"
    name = "Senior Responsibility"
    description = "Identifies evidence of senior responsibilities from experience titles and scope"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])

        areas: dict[str, Any] = {}
        refs: set[str] = set()

        for area_name in (
            "architecture",
            "devops",
            "platform_ownership",
            "migrations",
            "security",
            "operations",
            "mentoring",
        ):
            areas[area_name] = {"detected": False, "experiences": []}

        for exp in experiences:
            title = exp.get("title", "")
            scope = exp.get("scope", "")
            matched = detect_responsibility_areas(title, scope=scope)
            if not matched:
                continue
            exp_id = exp.get("id", "")
            org_name, _ = _org_name_and_id(exp, context)
            for area_name, keywords in matched.items():
                area = areas[area_name]
                if not area["detected"]:
                    area["detected"] = True
                area["experiences"].append(
                    {
                        "experience_id": exp_id,
                        "title": title,
                        "organization": org_name,
                        "matched_keywords": keywords,
                    }
                )
                refs.add(exp_id)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="senior_responsibility",
                value=areas,
                confidence=1.0,
                evidence_refs=tuple(sorted(refs)),
                metadata={
                    "areas_detected": [
                        name for name, a in areas.items() if a["detected"]
                    ],
                },
            )
        ]


# ---------------------------------------------------------------------------
# 7. CareerHighlightsRule
# ---------------------------------------------------------------------------


class CareerHighlightsRule(Rule):
    id = "career_highlights"
    name = "Career Highlights"
    description = "Extracts deterministic career highlights from profile data"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        skills = context.profile.get("skills", [])

        exp_skills = _build_exp_skills_map(context.profile)

        highlights: dict[str, Any] = {}

        highlights["longest_project"] = self._find_longest_project(
            experiences, context
        )
        highlights["highest_responsibility"] = self._find_highest_responsibility(
            experiences, context
        )
        highlights["longest_employer"] = self._find_longest_employer(
            experiences, context
        )
        highlights["largest_technology_stack"] = self._find_largest_tech_stack(
            experiences, skills, exp_skills, context
        )
        highlights["migration_experience"] = self._find_migration_experience(
            experiences, context
        )

        refs: set[str] = set()
        for exp in experiences:
            if exp.get("id"):
                refs.add(exp["id"])

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="career_highlights",
                value=highlights,
                confidence=1.0,
                evidence_refs=tuple(sorted(refs)),
                metadata={
                    "highlight_count": sum(
                        1 for v in highlights.values() if v is not None
                    ),
                },
            )
        ]

    @staticmethod
    def _find_longest_project(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> dict[str, Any] | None:
        best = None
        best_dur = -1.0
        for exp in experiences:
            dr = parse_date_range(exp.get("dateRange"))
            dur = duration_years(dr)
            if dur > best_dur:
                best_dur = dur
                best = exp
        if best is None:
            return None
        org_name, _ = _org_name_and_id(best, context)
        dr = best.get("dateRange", {})
        return {
            "title": best.get("title", ""),
            "organization": org_name,
            "duration_years": round(best_dur, 1),
            "formatted_duration": format_duration(best_dur),
            "start_date": dr.get("start", ""),
            "end_date": dr.get("end", ""),
        }

    @staticmethod
    def _find_highest_responsibility(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> dict[str, Any] | None:
        best = None
        best_tl = -1
        for exp in experiences:
            title = exp.get("title", "")
            tl = title_level(title)
            if tl > best_tl:
                best_tl = tl
                best = exp
        if best is None:
            return None
        org_name, _ = _org_name_and_id(best, context)
        return {
            "title": best.get("title", ""),
            "title_level": best_tl,
            "organization": org_name,
        }

    @staticmethod
    def _find_longest_employer(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> dict[str, Any] | None:
        org_groups: dict[str, dict[str, Any]] = {}
        for exp in experiences:
            org_name, org_id = _org_name_and_id(exp, context)
            key = org_id or org_name
            if key not in org_groups:
                org_groups[key] = {
                    "organization": org_name,
                    "organization_id": org_id,
                    "experiences": [],
                }
            org_groups[key]["experiences"].append(exp)

        best_key = None
        best_dur = -1.0
        for key, group in org_groups.items():
            total = total_experience_years(group["experiences"])
            if total > best_dur:
                best_dur = total
                best_key = key

        if best_key is None:
            return None
        group = org_groups[best_key]
        return {
            "organization": group["organization"],
            "total_years": round(best_dur, 1),
            "formatted_duration": format_duration(best_dur),
            "role_count": len(group["experiences"]),
        }

    @staticmethod
    def _find_largest_tech_stack(
        experiences: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        exp_skills: dict[str, list[str]],
        context: RuleContext,
    ) -> dict[str, Any] | None:
        org_groups: dict[str, dict[str, Any]] = {}
        for exp in experiences:
            org_name, org_id = _org_name_and_id(exp, context)
            key = org_id or org_name
            if key not in org_groups:
                org_groups[key] = {
                    "organization": org_name,
                    "organization_id": org_id,
                    "skill_names": set(),
                }
            exp_id = exp.get("id", "")
            org_groups[key]["skill_names"].update(exp_skills.get(exp_id, []))

        best_key = None
        best_count = -1
        for key, group in org_groups.items():
            cnt = len(group["skill_names"])
            if cnt > best_count:
                best_count = cnt
                best_key = key

        if best_key is None or best_count == 0:
            return None
        group = org_groups[best_key]
        return {
            "organization": group["organization"],
            "skill_count": best_count,
            "skills": sorted(group["skill_names"]),
        }

    @staticmethod
    def _find_migration_experience(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> dict[str, Any] | None:
        best = None
        best_dur = -1.0
        for exp in experiences:
            title = exp.get("title", "")
            scope = exp.get("scope", "")
            if not has_migration_keywords(title, scope=scope):
                continue
            dr = parse_date_range(exp.get("dateRange"))
            dur = duration_years(dr)
            if dur > best_dur:
                best_dur = dur
                best = exp
        if best is None:
            return None
        org_name, _ = _org_name_and_id(best, context)
        return {
            "title": best.get("title", ""),
            "organization": org_name,
            "duration_years": round(best_dur, 1),
            "formatted_duration": format_duration(best_dur),
        }
