from __future__ import annotations

from typing import Any, ClassVar

from ..person_data import ExperienceData
from ..utils import extract_month, extract_year, normalize_company, normalize_date
from .base import BaseBuilder, BuilderContext


class ExperienceBuilder(BaseBuilder):
    entity_type: ClassVar[type] = ExperienceData
    profile_key: ClassVar[str] = "experiences"
    extraction_field: ClassVar[str] = "experiences"

    def normalize(self, items: list) -> list:
        seen: set[tuple[str, str, str]] = set()
        unique: list[ExperienceData] = []

        for exp in items:
            if not isinstance(exp, ExperienceData):
                continue
            key = self._dedup_key(exp)
            if key not in seen:
                seen.add(key)
                unique.append(self._normalize_one(exp))

        unique.sort(key=self._sort_key, reverse=True)
        return unique

    def build_many(
        self,
        items: list,
        context: BuilderContext,
    ) -> list[dict[str, Any]]:
        self._collect_organizations(items, context)
        return [self._build_one(exp, context) for exp in items]

    def _normalize_one(self, exp: ExperienceData) -> ExperienceData:
        return ExperienceData(
            id=exp.id,
            organization=exp.organization.strip(),
            title=exp.title.strip(),
            employment_type=exp.employment_type.strip() if exp.employment_type else None,
            location=exp.location.strip() if exp.location else None,
            start_date=normalize_date(exp.start_date) if exp.start_date else None,
            end_date=normalize_date(exp.end_date) if exp.end_date else None,
            is_current=exp.is_current,
            summary=exp.summary.strip() if exp.summary else None,
            responsibilities=[r.strip() for r in exp.responsibilities if r.strip()],
            achievements=[a.strip() for a in exp.achievements if a.strip()],
            technologies=[t.strip() for t in exp.technologies if t.strip()],
            source_ref=exp.source_ref.strip() if exp.source_ref else None,
        )

    def _dedup_key(self, exp: ExperienceData) -> tuple[str, str, str]:
        org = normalize_company(exp.organization)
        title = exp.title.strip().lower()
        dates = f"{exp.start_date or ''}|{exp.end_date or ''}"
        return (org, title, dates)

    @staticmethod
    def _sort_key(exp: ExperienceData) -> tuple[int, int, int]:
        year = extract_year(exp.start_date)
        month = extract_month(exp.start_date)
        return (year or 0, month or 0, 0)

    def _collect_organizations(
        self,
        items: list[ExperienceData],
        context: BuilderContext,
    ) -> None:
        names_by_key: dict[str, str] = {}
        for exp in items:
            key = normalize_company(exp.organization)
            oid = f"org-{key.replace(' ', '-')}"
            if key not in names_by_key:
                context.organization_id_map[key] = oid
                names_by_key[key] = exp.organization.strip()
            else:
                existing = names_by_key[key]
                if len(exp.organization.strip()) < len(existing):
                    names_by_key[key] = exp.organization.strip()
        context.organization_names = names_by_key

    def _build_one(
        self,
        exp: ExperienceData,
        context: BuilderContext,
    ) -> dict[str, Any]:
        org_key = normalize_company(exp.organization)
        entry: dict[str, Any] = {
            "id": exp.id,
            "title": exp.title,
        }

        if org_key in context.organization_id_map:
            oid = context.organization_id_map[org_key]
            entry["organizationRefs"] = [{"id": oid, "type": "organization"}]

        date_range: dict[str, Any] = {}
        if exp.start_date:
            date_range["start"] = exp.start_date
        if exp.end_date:
            date_range["end"] = exp.end_date
        if exp.is_current is not None:
            date_range["isCurrent"] = exp.is_current
        else:
            date_range["isCurrent"] = True
        if date_range:
            entry["dateRange"] = date_range

        if exp.location:
            entry["location"] = {"label": exp.location}

        if exp.employment_type:
            entry["engagementType"] = exp.employment_type

        if exp.summary:
            entry["scope"] = exp.summary

        context.experience_id_map[exp.id] = exp.title
        return entry
