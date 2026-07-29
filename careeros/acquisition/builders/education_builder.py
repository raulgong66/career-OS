from __future__ import annotations

from typing import Any, ClassVar

from ..person_data import EducationData
from ..utils import extract_month, extract_year, normalize_date
from .base import BaseBuilder, BuilderContext


INSTITUTION_ALIASES: dict[str, str] = {
    "mit": "Massachusetts Institute of Technology",
    "massachusetts institute of technology": "Massachusetts Institute of Technology",
    "kth": "KTH Royal Institute of Technology",
    "royal institute of technology": "KTH Royal Institute of Technology",
    "kth royal institute of technology": "KTH Royal Institute of Technology",
    "harvard": "Harvard University",
    "harvard university": "Harvard University",
    "stanford": "Stanford University",
    "stanford university": "Stanford University",
    "oxford": "University of Oxford",
    "oxford university": "University of Oxford",
    "cambridge": "University of Cambridge",
    "cambridge university": "University of Cambridge",
    "uc berkeley": "University of California, Berkeley",
    "berkeley": "University of California, Berkeley",
}


class EducationBuilder(BaseBuilder):
    entity_type: ClassVar[type] = EducationData
    profile_key: ClassVar[str] = "education"
    extraction_field: ClassVar[str] = "education"

    def normalize(self, items: list) -> list:
        seen: set[tuple[str, str, str]] = set()
        unique: list[EducationData] = []

        for edu in items:
            if not isinstance(edu, EducationData):
                continue
            key = self._dedup_key(edu)
            if key not in seen:
                seen.add(key)
                unique.append(self._normalize_one(edu))

        unique.sort(key=self._sort_key, reverse=True)
        return unique

    def build_many(
        self,
        items: list,
        context: BuilderContext,
    ) -> list[dict[str, Any]]:
        return [self._build_one(edu) for edu in items]

    def _normalize_one(self, edu: EducationData) -> EducationData:
        institution = edu.institution.strip()
        canonical = INSTITUTION_ALIASES.get(institution.lower(), institution)
        start_date = normalize_date(edu.start_date) if edu.start_date else None
        end_date = normalize_date(edu.end_date) if edu.end_date else None
        is_current = edu.is_current
        if is_current is None and end_date == "":
            is_current = True
        return EducationData(
            institution=canonical,
            degree=edu.degree.strip(),
            field_of_study=edu.field_of_study.strip() if edu.field_of_study else None,
            start_date=start_date,
            end_date=end_date if end_date else None,
            is_current=is_current,
            location=edu.location.strip() if edu.location else None,
            description=edu.description.strip() if edu.description else None,
            confidence=edu.confidence,
            source_reference=edu.source_reference.strip() if edu.source_reference else None,
        )

    @staticmethod
    def _dedup_key(edu: EducationData) -> tuple[str, str, str]:
        raw = edu.institution.strip().lower()
        inst = INSTITUTION_ALIASES.get(raw, raw)
        degree = edu.degree.strip().lower()
        dates = f"{edu.start_date or ''}|{edu.end_date or ''}"
        return (inst, degree, dates)

    @staticmethod
    def _sort_key(edu: EducationData) -> tuple[int, int, int]:
        year = extract_year(edu.start_date)
        month = extract_month(edu.start_date)
        return (year or 0, month or 0, 0)

    @staticmethod
    def _build_one(edu: EducationData) -> dict[str, Any]:
        inst_key = edu.institution.lower().replace(" ", "-").replace(",", "")
        inst_id = f"org-{inst_key}"
        entry: dict[str, Any] = {
            "id": f"edu-{inst_key}-{edu.degree.lower().replace(' ', '-')}",
            "institutionRef": {"id": inst_id, "type": "organization"},
            "program": edu.degree,
        }
        if edu.field_of_study:
            entry["fieldOfStudy"] = edu.field_of_study
        date_range: dict[str, Any] = {}
        if edu.start_date:
            date_range["start"] = edu.start_date
        if edu.end_date:
            date_range["end"] = edu.end_date
        if edu.is_current is not None:
            date_range["isCurrent"] = edu.is_current
        elif not edu.end_date:
            date_range["isCurrent"] = True
        if date_range:
            entry["dateRange"] = date_range
        return entry
