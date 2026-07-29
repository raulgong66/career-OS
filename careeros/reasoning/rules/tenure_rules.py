from __future__ import annotations

from typing import Any

from careeros.reasoning import ReasoningResult, Rule, RuleContext
from careeros.reasoning.utils import (
    duration_years,
    employment_gaps,
    format_duration,
    merge_overlapping_periods,
    parse_date_range,
    title_level,
    total_experience_years,
)

_GAP_THRESHOLD_KEY = "employment_gap_min_days"


class TotalYearsExperienceRule(Rule):
    id = "total_years_experience"
    name = "Total Years of Experience"
    description = "Calculates total professional experience years, merging overlapping periods"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        total = total_experience_years(experiences)
        exp_ids = tuple(
            e["id"] for e in experiences if "id" in e
        )
        periods = [
            parse_date_range(e.get("dateRange")) for e in experiences
        ]
        merged = merge_overlapping_periods(periods)
        has_current = any(p.is_current for p in periods)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="total_years_of_experience",
                value=round(total, 1),
                confidence=1.0,
                evidence_refs=exp_ids,
                metadata={
                    "raw_years": round(total, 4),
                    "formatted": format_duration(total),
                    "experience_count": len(experiences),
                    "periods_after_merge": len(merged),
                    "has_current_employment": has_current,
                },
            )
        ]


class CurrentEmployerRule(Rule):
    id = "current_employer"
    name = "Current Employer"
    description = "Identifies the current employer, if any"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        current = self._find_current(experiences, context)
        refs: tuple[str, ...] = ()
        metadata: dict[str, Any] = {"has_current": False}

        if current is not None:
            org_name, org_id, exp_id = current
            refs = (exp_id, org_id) if org_id else (exp_id,)
            metadata = {
                "has_current": True,
                "organization_id": org_id or "",
                "experience_id": exp_id,
            }
            value: Any = org_name
        else:
            value = "none"

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="current_employer",
                value=value,
                confidence=1.0,
                evidence_refs=refs,
                metadata=metadata,
            )
        ]

    @staticmethod
    def _find_current(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> tuple[str, str | None, str] | None:
        latest_exp = None
        latest_start: str | None = None
        for exp in experiences:
            dr = parse_date_range(exp.get("dateRange"))
            if dr.is_current or (dr.end is None and dr.start is not None):
                exp_id = exp.get("id", "")
                start_str = (
                    exp.get("dateRange", {}).get("start") if exp.get("dateRange") else None
                )
                if latest_exp is None or (
                    start_str is not None
                    and (latest_start is None or start_str > latest_start)
                ):
                    latest_exp = exp
                    latest_start = start_str
        if latest_exp is None:
            return None
        exp_id = latest_exp.get("id", "")
        org_name, org_id = _org_name_and_id(latest_exp, context)
        return org_name, org_id, exp_id


class CurrentRoleRule(Rule):
    id = "current_role"
    name = "Current Role"
    description = "Identifies the current position title, if any"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        current = self._find_current_role(experiences)
        refs: tuple[str, ...] = ()
        metadata: dict[str, Any] = {"has_current": False}

        if current is not None:
            title, exp_id = current
            refs = (exp_id,)
            metadata = {
                "has_current": True,
                "experience_id": exp_id,
            }
            value: Any = title
        else:
            value = "none"

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="current_role",
                value=value,
                confidence=1.0,
                evidence_refs=refs,
                metadata=metadata,
            )
        ]

    @staticmethod
    def _find_current_role(
        experiences: list[dict[str, Any]],
    ) -> tuple[str, str] | None:
        latest = None
        latest_start: str | None = None
        for exp in experiences:
            dr = parse_date_range(exp.get("dateRange"))
            if dr.is_current or (dr.end is None and dr.start is not None):
                start_str = (
                    exp.get("dateRange", {}).get("start") if exp.get("dateRange") else None
                )
                if latest is None or (
                    start_str is not None
                    and (latest_start is None or start_str > latest_start)
                ):
                    latest = exp
                    latest_start = start_str
        if latest is None:
            return None
        title = latest.get("title", "Unknown")
        return title, latest.get("id", "")


class LongestTenureRule(Rule):
    id = "longest_tenure"
    name = "Longest Tenure"
    description = "Identifies the longest continuous employment"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        longest = self._find_longest(experiences, context)

        if longest is not None:
            exp, org_name, org_id, dur = longest
            exp_id = exp.get("id", "")
            dr = exp.get("dateRange", {})
            value: Any = {
                "employer": org_name,
                "role": exp.get("title", ""),
                "duration_years": round(dur, 1),
                "formatted_duration": format_duration(dur),
                "start_date": dr.get("start", ""),
                "end_date": dr.get("end", ""),
            }
            refs: tuple[str, ...] = (exp_id, org_id) if org_id else (exp_id,)
            metadata: dict[str, Any] = {
                "organization_id": org_id or "",
                "experience_id": exp_id,
                "duration_years": round(dur, 4),
            }
        else:
            value = "none"
            refs = ()
            metadata = {}

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="longest_tenure",
                value=value,
                confidence=1.0,
                evidence_refs=refs,
                metadata=metadata,
            )
        ]

    @staticmethod
    def _find_longest(
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> tuple[dict[str, Any], str, str | None, float] | None:
        best = None
        best_dur = -1.0
        for exp in experiences:
            dr = parse_date_range(exp.get("dateRange"))
            dur = duration_years(dr)
            if dur > best_dur:
                best = exp
                best_dur = dur
        if best is None:
            return None
        org_name, org_id = _org_name_and_id(best, context)
        return best, org_name, org_id, best_dur


class CareerProgressionRule(Rule):
    id = "career_progression"
    name = "Career Progression"
    description = "Produces a chronological timeline with promotions and organization changes"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        timeline = self._build_timeline(experiences, context)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="career_progression_timeline",
                value=timeline,
                confidence=1.0,
                evidence_refs=tuple(
                    e["id"] for e in experiences if "id" in e
                ),
                metadata={
                    "total_events": len(timeline.get("events", [])),
                    "promotions": timeline.get("summary", {}).get("promotions", 0),
                    "org_changes": timeline.get("summary", {}).get("org_changes", 0),
                },
            )
        ]

    def _build_timeline(
        self,
        experiences: list[dict[str, Any]],
        context: RuleContext,
    ) -> dict[str, Any]:
        sorted_exps = self._sort_experiences(experiences)
        events: list[dict[str, Any]] = []
        promotions = 0
        org_changes = 0
        prev_org_id: str | None = None
        prev_title: str | None = None

        org_groups: dict[str, list[dict[str, Any]]] = {}
        for exp in sorted_exps:
            _, org_id = _org_name_and_id(exp, context)
            gid = org_id or "__no_org__"
            org_groups.setdefault(gid, []).append(exp)

        for exp in sorted_exps:
            exp_id = exp.get("id", "")
            title = exp.get("title", "")
            org_name, org_id = _org_name_and_id(exp, context)
            dr = exp.get("dateRange", {})
            start_str = dr.get("start", "")
            end_str = dr.get("end", "")

            events.append(
                {
                    "date": start_str,
                    "type": "role_start",
                    "title": title,
                    "organization": org_name,
                    "organization_id": org_id or "",
                    "experience_id": exp_id,
                }
            )
            if end_str:
                events.append(
                    {
                        "date": end_str,
                        "type": "role_end",
                        "title": title,
                        "organization": org_name,
                        "organization_id": org_id or "",
                        "experience_id": exp_id,
                    }
                )

            if prev_org_id is not None and org_id is not None and org_id != prev_org_id:
                org_changes += 1
            if (
                prev_org_id is not None
                and org_id is not None
                and org_id == prev_org_id
                and prev_title is not None
                and title != prev_title
            ):
                promotions += 1

            if org_id:
                prev_org_id = org_id
            prev_title = title

        pattern = self._classify_pattern(promotions, org_changes, len(sorted_exps))

        events.sort(key=lambda e: (e.get("date") or "0000", e.get("type", "")))
        summary = {
            "total_roles": len(sorted_exps),
            "total_organizations": len(
                [g for g in org_groups if g != "__no_org__"]
            ),
            "promotions": promotions,
            "org_changes": org_changes,
            "pattern": pattern,
        }
        return {"events": events, "summary": summary}

    @staticmethod
    def _sort_experiences(
        experiences: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        def sort_key(exp: dict[str, Any]) -> str:
            dr = exp.get("dateRange", {}) or {}
            return dr.get("start", "") or "9999-99"

        return sorted(experiences, key=sort_key)

    @staticmethod
    def _classify_pattern(
        promotions: int,
        org_changes: int,
        total_roles: int,
    ) -> str:
        if total_roles <= 1:
            return "single_role"
        if promotions > 0 and org_changes == 0:
            return "upward"
        if promotions > 0 and org_changes > 0:
            return "varied"
        if org_changes > 0 and promotions == 0:
            return "lateral"
        return "stable"


class EmploymentGapRule(Rule):
    id = "employment_gap"
    name = "Employment Gaps"
    description = "Detects employment gaps longer than a configurable threshold"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        min_days = context.parameters.get(_GAP_THRESHOLD_KEY, 30)
        gaps = employment_gaps(experiences, min_gap_days=min_days)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="employment_gap",
                value=gaps,
                confidence=1.0,
                evidence_refs=tuple(
                    e.get("id", "") for e in experiences if "id" in e
                ),
                metadata={
                    "gap_count": len(gaps),
                    "min_gap_days": min_days,
                    "total_gap_days": sum(g.get("duration_days", 0) for g in gaps),
                },
            )
        ]


class CareerStageRule(Rule):
    id = "career_stage"
    name = "Career Stage"
    description = "Classifies career stage using measurable profile evidence"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        experiences = context.profile.get("experiences", [])
        total_years = total_experience_years(experiences)

        max_tl = max(
            (title_level(e.get("title", "")) for e in experiences if e.get("title")),
            default=2,
        )

        stage = self._classify(total_years, max_tl)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="career_stage_classification",
                value=stage,
                confidence=1.0,
                evidence_refs=tuple(
                    e["id"] for e in experiences if "id" in e
                ),
                metadata={
                    "total_years": round(total_years, 1),
                    "highest_title_level": max_tl,
                    "experience_count": len(experiences),
                },
            )
        ]

    @staticmethod
    def _classify(total_years: float, _title_level: int) -> str:
        if total_years < 2:
            return "Early Career"
        if total_years < 5:
            return "Mid Career"
        if total_years < 10:
            return "Senior"
        if total_years < 15:
            return "Principal"
        return "Executive"


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
