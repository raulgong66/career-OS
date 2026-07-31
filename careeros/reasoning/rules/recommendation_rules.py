from __future__ import annotations

import re
from typing import Any

from careeros.reasoning import ReasoningResult, Rule, RuleContext
from careeros.reasoning.utils import word_boundary_match

from .skill_rules import SKILL_CATEGORIES

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

MAX_RECOMMENDATIONS_PER_RULE = 5

TECHNOLOGY_KEYWORDS: tuple[str, ...] = tuple(
    {
        keyword
        for keywords in SKILL_CATEGORIES.values()
        for keyword in keywords
    }
) + (
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "excel", "powerpoint", "microsoft office", "outlook",
    "linux", "unix", "windows", "macos",
    "xml", "json", "yaml", "toml", "rest", "api",
    "agile", "scrum", "kanban", "sprint",
    "sql", "nosql", "data", "analytics", "machine learning", "ai",
)

GENERIC_SUMMARY_WORDS: tuple[str, ...] = (
    "results-driven", "result driven", "detail-oriented", "detail oriented",
    "hard-working", "hard working", "self-starter", "self starter",
    "team player", "motivated", "dedicated", "passionate", "proactive",
    "fast learner", "problem solver", "multitasker",
)

BUSINESS_OUTCOME_WORDS: tuple[str, ...] = (
    "reduced", "increased", "improved", "decreased", "saved", "generated",
    "delivered", "achieved", "grew", "cut", "boosted", "optimized",
    "automated", "accelerated", "streamlined", "implemented",
    "revenue", "cost", "costs", "sales", "profit", "margin", "roi",
    "efficiency", "uptime", "availability", "performance", "latency",
    "turnaround", "productivity", "growth", "conversion", "retention",
    "throughput", "capacity", "scaling", "downtime", "outage",
    "usd", "eur", "million", "billion", "thousand",
)

NUMBER_PATTERN = re.compile(r"\d")

FUTURE_EVIDENCE_PLACEHOLDER: dict[str, Any] = {
    "evidence_model": "not_implemented",
}

# Deterministic, recruiter-quality example bullets (no AI generation).
EXAMPLES_MEASURABLE_ACHIEVEMENT: tuple[str, ...] = (
    "Reduced deployment time by 60%",
    "Migrated 240 servers to AWS",
    "Improved availability from 99.5% to 99.95%",
)

EXAMPLES_SHOW_SKILL: tuple[str, ...] = (
    "Used it to automate server provisioning across 40+ nodes",
    "Built a data pipeline that processed 1M records per day",
    "Wrote tooling that cut release build time by 30%",
)

EXAMPLES_ADD_TECHNOLOGIES: tuple[str, ...] = (
    "Led migration of 40 microservices to Kubernetes on AWS EKS",
    "Automated infrastructure with Terraform and Jenkins CI/CD",
    "Built Grafana dashboards on Prometheus metrics for 20 services",
)

EXAMPLES_SUMMARY: tuple[str, ...] = (
    "Senior DevOps engineer with 8 years scaling AWS infrastructure",
    "Cut deployment time by 40% and lifted uptime to 99.9%",
    "Led a team of 5 platform engineers serving 50+ product teams",
)

EXAMPLES_DUPLICATE_SKILLS: tuple[str, ...] = (
    "'AWS' and 'Amazon Web Services' merged into one 'AWS' entry",
    "'JavaScript' and 'Javascript' merged into one 'JavaScript' entry",
    "'Docker' and 'Docker Containers' merged into one 'Docker' entry",
)

EXAMPLES_BUSINESS_OUTCOME: tuple[str, ...] = (
    "Cut infrastructure cost by 25%",
    "Reduced incident response time from 4 hours to 30 minutes",
    "Grew daily active users by 18%",
)

EXAMPLES_CERTIFICATION: tuple[str, ...] = (
    "Applied AWS Solutions Architect practices to a cost-optimized migration",
    "Used CISSP principles to establish the first security review process",
    "Leveraged CKAD training to containerize 20 existing services",
)

EXAMPLES_PROJECT_SKILLS: tuple[str, ...] = (
    "Tag a CI/CD project with 'Docker', 'Kubernetes', 'CI/CD'",
    "Tag a data project with 'Python', 'SQL', 'Airflow'",
    "Link a cloud migration project to your platform engineering experience",
)

EXPLANATION_MEASURABLE_ACHIEVEMENT = (
    "Recruiters scan for quantified impact; an experience that only describes "
    "responsibilities looks like every other job description."
)

EXPLANATION_SHOW_SKILL = (
    "Skills without demonstrated use can read as inflated — reviewers trust "
    "what they can see in context."
)

EXPLANATION_ADD_TECHNOLOGIES = (
    "Descriptions without tools and technologies give reviewers no way to "
    "gauge your technical depth."
)

EXPLANATION_SUMMARY = (
    "Your summary is the first thing most recruiters read — without it, they "
    "have to infer your strengths from the rest of the profile."
)

EXPLANATION_DUPLICATE_SKILLS = (
    "Duplicate entries split your evidence across two skills and can look "
    "careless to reviewers."
)

EXPLANATION_BUSINESS_OUTCOME = (
    "Recruiters hire for outcomes; activity alone does not show the value you "
    "delivered."
)

EXPLANATION_CERTIFICATION = (
    "Certifications earn credibility when they are tied to real work — "
    "otherwise they are just a line item."
)

EXPLANATION_PROJECT_SKILLS = (
    "Projects that are not connected to skills cannot strengthen your skill "
    "evidence."
)


def _experience_text(exp: dict[str, Any]) -> str:
    return " ".join(
        str(exp.get(key, "") or "") for key in ("title", "scope")
    ).lower()


def _skill_text(skill_name: str) -> str:
    return skill_name.lower()


def _limit(items: list[ReasoningResult]) -> list[ReasoningResult]:
    return items[:MAX_RECOMMENDATIONS_PER_RULE]


def _build_recommendation(
    rule_id: str,
    finding_type: str,
    title: str,
    reason: str,
    explanation: str,
    suggested_action: str,
    examples: tuple[str, ...],
    priority: str,
    estimated_impact: str,
    element_id: str | None,
    element_type: str | None,
    confidence: str,
) -> ReasoningResult:
    return ReasoningResult(
        rule_id=rule_id,
        finding_type=finding_type,
        value={
            "title": title,
            "reason": reason,
            "explanation": explanation,
            "suggested_action": suggested_action,
            "examples": list(examples),
            "priority": priority,
            "estimated_impact": estimated_impact,
            "element_id": element_id,
            "element_type": element_type,
            "confidence": confidence,
            "future_evidence": dict(FUTURE_EVIDENCE_PLACEHOLDER),
        },
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# 1. Experiences without measurable achievements
# ---------------------------------------------------------------------------


class NoMeasurableAchievementRule(Rule):
    id = "recommendation_add_measurable_achievement"
    name = "Experiences Without Measurable Achievements"
    description = (
        "Flags experiences that lack measurable achievements, or whose linked "
        "achievements contain no quantitative or business-outcome content"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        achievements_by_id = {
            a.get("id"): a for a in context.profile.get("achievements", [])
        }

        for exp in context.profile.get("experiences", []):
            exp_title = str(exp.get("title", "") or "").strip() or "this role"
            refs = exp.get("achievementRefs", []) or []
            ref_ids = [r.get("id") for r in refs if isinstance(r, dict) and r.get("id")]

            if not ref_ids:
                results.append(
                    _build_recommendation(
                        rule_id=self.id,
                        finding_type=self.id,
                        title="Add measurable achievements",
                        reason=(
                            f"'{exp_title}' has no achievements listed — it describes "
                            "responsibilities without evidence of results."
                        ),
                        explanation=EXPLANATION_MEASURABLE_ACHIEVEMENT,
                        suggested_action=(
                            "Add at least one measurable achievement to this experience."
                        ),
                        examples=EXAMPLES_MEASURABLE_ACHIEVEMENT,
                        priority="high",
                        estimated_impact="high",
                        element_id=exp.get("id"),
                        element_type="experience",
                        confidence="high",
                    )
                )
                continue

            measurable = any(
                _is_measurable(achievements_by_id.get(rid))
                for rid in ref_ids
                if rid in achievements_by_id
            )
            if not measurable:
                results.append(
                    _build_recommendation(
                        rule_id=self.id,
                        finding_type=self.id,
                        title="Quantify achievements with outcomes",
                        reason=(
                            f"'{exp_title}' lists achievements, but none include a "
                            "measurable outcome (metrics, percentages, or business impact)."
                        ),
                        explanation=EXPLANATION_MEASURABLE_ACHIEVEMENT,
                        suggested_action=(
                            "Rewrite each achievement to state a quantified result — "
                            "a metric, percentage, or business outcome."
                        ),
                        examples=EXAMPLES_MEASURABLE_ACHIEVEMENT,
                        priority="high",
                        estimated_impact="high",
                        element_id=exp.get("id"),
                        element_type="experience",
                        confidence="medium",
                    )
                )

        return _limit(results)


def _is_measurable(achievement: dict[str, Any] | None) -> bool:
    if not achievement:
        return False
    metrics = achievement.get("metrics", [])
    if metrics and any(str(m).strip() for m in metrics):
        return True
    description = str(achievement.get("description", "") or "")
    impact = str(achievement.get("impact", "") or "")
    combined = f"{description} {impact}"
    if NUMBER_PATTERN.search(combined):
        return True
    return any(word_boundary_match(word, combined) for word in BUSINESS_OUTCOME_WORDS)


# ---------------------------------------------------------------------------
# 2. Skills never demonstrated in experience
# ---------------------------------------------------------------------------


class SkillWithoutExperienceRule(Rule):
    id = "recommendation_show_skill_in_experience"
    name = "Skills Never Demonstrated in Experience"
    description = (
        "Flags skills that are not referenced by any experience, achievement, "
        "or explicit experience evidence, suggesting they may be unsubstantiated"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        experiences = context.profile.get("experiences", [])
        achievements = context.profile.get("achievements", [])
        searchable_text = " ".join(
            [
                _experience_text(exp) for exp in experiences
            ]
            + [
                str(a.get("title", "") or "") + " " + str(a.get("description", "") or "")
                for a in achievements
            ]
        ).lower()

        for skill in context.profile.get("skills", []):
            skill_id = skill.get("id")
            skill_name = str(skill.get("name", "") or "").strip()
            if not skill_name:
                continue
            lower = _skill_text(skill_name)

            experience_evidence = (
                skill.get("extensions", {}).get("experienceEvidence") or []
            )
            if experience_evidence:
                continue
            if context.graph.experiences_using(skill_name):
                continue
            if word_boundary_match(lower, searchable_text):
                continue

            category = skill.get("category", "")
            confidence = "high" if category else "medium"
            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Show how you use this skill",
                    reason=(
                        f"'{skill_name}' is listed as a skill but never appears in your "
                        "experience or achievements."
                    ),
                    explanation=EXPLANATION_SHOW_SKILL,
                    suggested_action=(
                        f"Add a concrete example that shows how you use {skill_name} "
                        "to an experience or achievement."
                    ),
                    examples=EXAMPLES_SHOW_SKILL,
                    priority="high" if category else "medium",
                    estimated_impact="medium",
                    element_id=skill_id,
                    element_type="skill",
                    confidence=confidence,
                )
            )

        return _limit(results)


# ---------------------------------------------------------------------------
# 3. Experiences without technology keywords
# ---------------------------------------------------------------------------


class ExperienceNoTechnologiesRule(Rule):
    id = "recommendation_add_technologies"
    name = "Experiences Without Technologies"
    description = (
        "Flags experiences whose description mentions no recognizable technology "
        "or tool, making them too vague for reviewers"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        for exp in context.profile.get("experiences", []):
            scope = str(exp.get("scope", "") or "").strip()
            exp_title = str(exp.get("title", "") or "").strip() or "this role"
            combined = _experience_text(exp)

            has_technology = any(
                word_boundary_match(kw, combined) for kw in TECHNOLOGY_KEYWORDS
            )
            if has_technology:
                continue

            if not scope:
                reason = (
                    f"'{exp_title}' has no description at all — nothing tells a reviewer "
                    "what you did or what you used."
                )
                priority = "high"
                confidence = "high"
            else:
                reason = (
                    f"'{exp_title}' describes work without naming any specific tool or "
                    "technology."
                )
                priority = "medium"
                confidence = "medium"

            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Name the technologies you used",
                    reason=reason,
                    explanation=EXPLANATION_ADD_TECHNOLOGIES,
                    suggested_action=(
                        "Describe your responsibilities and name the tools and "
                        "technologies you used (e.g., Python, AWS, Kubernetes)."
                    ),
                    examples=EXAMPLES_ADD_TECHNOLOGIES,
                    priority=priority,
                    estimated_impact="high",
                    element_id=exp.get("id"),
                    element_type="experience",
                    confidence=confidence,
                )
            )

        return _limit(results)


# ---------------------------------------------------------------------------
# 4. Generic or missing professional summary
# ---------------------------------------------------------------------------


class GenericSummaryRule(Rule):
    id = "recommendation_improve_summary"
    name = "Generic or Missing Professional Summary"
    description = (
        "Flags profiles without a professional summary, or with a summary that is "
        "too short, too generic, or lacking measurable substance"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        summaries = context.profile.get("professionalSummaries", []) or []
        texts = [
            str(s.get("text", "") or "").strip()
            for s in summaries
            if isinstance(s, dict)
        ]
        texts = [t for t in texts if t]
        combined = " ".join(texts).lower()

        if not texts:
            return [
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Add a professional summary",
                    reason="Your profile has no professional summary.",
                    explanation=EXPLANATION_SUMMARY,
                    suggested_action=(
                        "Write 2-3 lines covering your role, your strongest skills, "
                        "and one quantified highlight."
                    ),
                    examples=EXAMPLES_SUMMARY,
                    priority="high",
                    estimated_impact="high",
                    element_id=None,
                    element_type="profile",
                    confidence="high",
                )
            ]

        has_number = NUMBER_PATTERN.search(combined) is not None
        has_technology = any(
            word_boundary_match(kw, combined) for kw in TECHNOLOGY_KEYWORDS
        )
        generic_hits = sum(
            1 for w in GENERIC_SUMMARY_WORDS if word_boundary_match(w, combined)
        )
        too_short = len(combined) < 40

        if too_short or (not has_number and not has_technology) or generic_hits >= 2:
            confidence = "medium" if not too_short else "low"
            return [
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Strengthen your professional summary",
                    reason="Your professional summary reads as generic.",
                    explanation=(
                        "Generic adjectives do not differentiate you from other "
                        "candidates."
                    ),
                    suggested_action=(
                        "Lead with your specialty, name key technologies, and include "
                        "a quantified result."
                    ),
                    examples=EXAMPLES_SUMMARY,
                    priority="medium",
                    estimated_impact="medium",
                    element_id=None,
                    element_type="profile",
                    confidence=confidence,
                )
            ]

        return []


# ---------------------------------------------------------------------------
# 5. Duplicate skills
# ---------------------------------------------------------------------------


class DuplicateSkillsRule(Rule):
    id = "recommendation_remove_duplicate_skills"
    name = "Duplicate Skills"
    description = (
        "Flags near-duplicate skill entries (e.g. 'Python' vs 'python', "
        "'AWS' vs 'amazon web services') that should be merged"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        normalized: dict[str, list[str]] = {}

        for skill in context.profile.get("skills", []):
            skill_name = str(skill.get("name", "") or "").strip()
            if not skill_name:
                continue
            key = _normalize_skill_name(skill_name)
            if not key:
                continue
            normalized.setdefault(key, []).append(skill_name)

        for names in normalized.values():
            unique = _dedupe_preserving_order(names)
            if len(unique) < 2:
                continue
            merged = " and ".join(f"'{n}'" for n in unique)
            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Merge duplicate skills",
                    reason=f"{merged} appear to be the same skill.",
                    explanation=EXPLANATION_DUPLICATE_SKILLS,
                    suggested_action=(
                        "Merge them into one skill entry and keep the strongest "
                        "evidence for it."
                    ),
                    examples=EXAMPLES_DUPLICATE_SKILLS,
                    priority="low",
                    estimated_impact="low",
                    element_id=None,
                    element_type="profile",
                    confidence="medium",
                )
            )

        return _limit(results)


def _normalize_skill_name(name: str) -> str:
    norm = re.sub(r"[^a-z0-9+#. ]", " ", name.lower())
    norm = re.sub(r"\s+", " ", norm).strip()
    if len(norm) > 3 and norm.endswith("s") and not norm.endswith("ss"):
        norm = norm[:-1]
    return norm


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# 6. Achievements without a measurable business outcome
# ---------------------------------------------------------------------------


class MissingBusinessOutcomeRule(Rule):
    id = "recommendation_add_business_outcome"
    name = "Achievements Without Business Outcomes"
    description = (
        "Flags achievements that describe activity without a measurable business "
        "outcome, reducing their persuasive power"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        for achievement in context.profile.get("achievements", []):
            title = str(achievement.get("title", "") or "").strip() or "this achievement"
            if _is_measurable(achievement):
                continue
            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Add a measurable business outcome",
                    reason=(
                        f"'{title}' describes activity but not a result — reviewers "
                        "cannot see the value it delivered."
                    ),
                    explanation=EXPLANATION_BUSINESS_OUTCOME,
                    suggested_action=(
                        "State the outcome of this achievement and quantify it "
                        "where possible."
                    ),
                    examples=EXAMPLES_BUSINESS_OUTCOME,
                    priority="medium",
                    estimated_impact="high",
                    element_id=achievement.get("id"),
                    element_type="achievement",
                    confidence="medium",
                )
            )
        return _limit(results)


# ---------------------------------------------------------------------------
# 7. Certifications not referenced anywhere
# ---------------------------------------------------------------------------


class CertificationUnreferencedRule(Rule):
    id = "recommendation_show_certification_value"
    name = "Certifications Not Referenced in Experience"
    description = (
        "Flags certifications that are listed but never connected to experience "
        "or achievements, so their value is not demonstrated"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        experiences = context.profile.get("experiences", [])
        achievements = context.profile.get("achievements", [])
        searchable_text = " ".join(
            [_experience_text(exp) for exp in experiences]
            + [
                str(a.get("title", "") or "") + " " + str(a.get("description", "") or "")
                for a in achievements
            ]
        ).lower()

        for cert in context.profile.get("certifications", []):
            cert_name = str(cert.get("name", "") or "").strip()
            if not cert_name:
                continue
            cert_id = cert.get("id")
            if cert.get("evidenceRefs"):
                continue
            if word_boundary_match(cert_name.lower(), searchable_text):
                continue

            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Show the value of this certification",
                    reason=(
                        f"'{cert_name}' is listed but never connected to your "
                        "experience or achievements."
                    ),
                    explanation=EXPLANATION_CERTIFICATION,
                    suggested_action=(
                        "Mention where you applied this certification, or reference "
                        "it in a relevant achievement."
                    ),
                    examples=EXAMPLES_CERTIFICATION,
                    priority="medium",
                    estimated_impact="medium",
                    element_id=cert_id,
                    element_type="certification",
                    confidence="medium",
                )
            )
        return _limit(results)


# ---------------------------------------------------------------------------
# 8. Projects without skill references
# ---------------------------------------------------------------------------


class ProjectWithoutSkillsRule(Rule):
    id = "recommendation_add_skills_to_project"
    name = "Projects Without Skills"
    description = (
        "Flags projects that are not tagged with the skills they demonstrate, "
        "making their evidence hard to connect to the skill graph"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        for project in context.profile.get("projects", []):
            title = str(project.get("title", "") or "").strip() or "This project"
            skill_refs = project.get("skillRefs", []) or []
            experience_refs = project.get("experienceRefs", []) or []
            if skill_refs:
                continue
            if experience_refs:
                continue

            results.append(
                _build_recommendation(
                    rule_id=self.id,
                    finding_type=self.id,
                    title="Tag this project with skills",
                    reason=(
                        f"'{title}' is not linked to any skills or experiences."
                    ),
                    explanation=EXPLANATION_PROJECT_SKILLS,
                    suggested_action=(
                        "Tag the project with the skills it demonstrates, or link it "
                        "to a related experience."
                    ),
                    examples=EXAMPLES_PROJECT_SKILLS,
                    priority="low",
                    estimated_impact="medium",
                    element_id=project.get("id"),
                    element_type="project",
                    confidence="low",
                )
            )
        return _limit(results)
