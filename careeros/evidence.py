"""Deterministic, reusable evidence matching for CareerOS profiles (Phase 3B).

This module provides the smallest deterministic foundation for a trusted
professional evidence layer. It pairs entities across two profiles that
represent the same real-world fact but were stored under different IDs
(e.g. ``exp-qred-bank2`` in one profile and ``exp-acmecorp2`` in another).

Design guarantees:

* deterministic: pure functions, sorted iteration, one-to-one greedy pairing
* read-only: never mutates profiles or entities
* provenance-aware: every match records the ``matched_on`` signals that
  justify it
* auditable: signals are explicit and machine-readable

The ``EntityEvidenceMatch`` representation is intentionally generic so it can
be reused by downstream consumers (staffing, assessment, workforce planning,
proposals, AI) without rerunning the heuristics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .acquisition.utils import extract_month, extract_year, normalize_company


@dataclass(frozen=True)
class EntityEvidenceMatch:
    """A deterministic cross-ID match between two entities of the same type.

    ``left_entity_id`` and ``right_entity_id`` are the differing IDs that were
    found to represent the same real-world fact. ``matched_on`` lists the
    evidence signals used (e.g. ``("title", "dateRange")``).
    """

    entity_type: str
    left_entity_id: str
    right_entity_id: str
    matched_on: tuple[str, ...] = ()


_OPEN_ENDED = (9999, 12)


def _tokens(value: str | None) -> set[str]:
    """Lowercase alphanumeric token set for a text value."""
    if not value:
        return set()
    folded = re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    return {tok for tok in folded.split() if tok}


def _norm_text(value: str | None) -> str:
    return " ".join(sorted(_tokens(value)))


_NUMERIC_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def _date_key(value: Any) -> tuple[int, int] | None:
    """Parse a ``YYYY-MM`` (or ``YYYY``) date string to a comparable key."""
    if not value:
        return None
    text = str(value).strip()
    numeric = _NUMERIC_MONTH.match(text)
    if numeric:
        return (int(numeric.group(1)), int(numeric.group(2)))
    year = extract_year(text)
    if year is None:
        return None
    month = extract_month(text)
    return (year, month or 1)


def _range_bounds(entity: Mapping[str, Any]) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Return (start, end) date keys for an entity's dateRange.

    A missing ``end`` on a current role is treated as open-ended. A missing
    ``start`` yields ``(None, None)`` (cannot be compared).
    """
    date_range = entity.get("dateRange") or {}
    if not isinstance(date_range, Mapping):
        return None, None
    start = _date_key(date_range.get("start"))
    if start is None:
        return None, None
    end = _date_key(date_range.get("end"))
    if end is None and date_range.get("isCurrent"):
        end = _OPEN_ENDED
    return start, end


def _dates_exact(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    sa, ea = _range_bounds(a)
    sb, eb = _range_bounds(b)
    return sa is not None and sb is not None and sa == sb and ea == eb


def _dates_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    sa, ea = _range_bounds(a)
    sb, eb = _range_bounds(b)
    if sa is None or sb is None:
        return False
    ea = ea or _OPEN_ENDED
    eb = eb or _OPEN_ENDED
    return sa <= eb and sb <= ea


def _first_ref_id(entity: Mapping[str, Any], key: str) -> str | None:
    """Extract the first ``id`` from a ref list or a single ref mapping."""
    refs = entity.get(key)
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, Mapping) and ref.get("id"):
                return str(ref["id"])
        return None
    if isinstance(refs, Mapping):
        return str(refs["id"]) if refs.get("id") else None
    return None


def _org_name_for(ref_id: str | None, org_names: Mapping[str, str]) -> str:
    if not ref_id:
        return ""
    return org_names.get(ref_id, "")


def _experience_score(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    a_org_names: Mapping[str, str],
    b_org_names: Mapping[str, str],
) -> tuple[int, tuple[str, ...]]:
    signals: list[str] = []
    score = 0

    ta = _tokens(a.get("title"))
    tb = _tokens(b.get("title"))
    if ta and tb and _norm_text(a.get("title")) == _norm_text(b.get("title")):
        score += 2
        signals.append("title")
    elif ta and tb and (ta <= tb or tb <= ta):
        score += 1
        signals.append("title-tokens")

    if _dates_exact(a, b):
        score += 2
        signals.append("dateRange")
    elif _dates_overlap(a, b):
        score += 1
        signals.append("dateRange-overlap")

    oa = _org_name_for(_first_ref_id(a, "organizationRefs"), a_org_names)
    ob = _org_name_for(_first_ref_id(b, "organizationRefs"), b_org_names)
    if oa and ob and normalize_company(oa) == normalize_company(ob):
        score += 1
        signals.append("organization")

    if signals and signals[0] in ("title", "title-tokens") and score >= 3:
        return score, tuple(signals)
    return 0, ()


def _organization_score(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    a_org_names: Mapping[str, str],
    b_org_names: Mapping[str, str],
) -> tuple[int, tuple[str, ...]]:
    na = normalize_company(a.get("name"))
    nb = normalize_company(b.get("name"))
    if na and nb and na == nb:
        return 2, ("name",)
    return 0, ()


def _skill_score(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    a_org_names: Mapping[str, str],
    b_org_names: Mapping[str, str],
) -> tuple[int, tuple[str, ...]]:
    ta = _tokens(a.get("name"))
    tb = _tokens(b.get("name"))
    if not ta or not tb:
        return 0, ()
    if ta == tb:
        return 3, ("name",)
    if ta <= tb or tb <= ta:
        return 2, ("name-tokens",)
    return 0, ()


def _education_score(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    a_org_names: Mapping[str, str],
    b_org_names: Mapping[str, str],
) -> tuple[int, tuple[str, ...]]:
    signals: list[str] = []
    score = 0

    pa = _norm_text(a.get("program"))
    pb = _norm_text(b.get("program"))
    if pa and pb and pa == pb:
        score += 2
        signals.append("program")

    ia = _org_name_for(_first_ref_id(a, "institutionRef"), a_org_names)
    ib = _org_name_for(_first_ref_id(b, "institutionRef"), b_org_names)
    if ia and ib and normalize_company(ia) == normalize_company(ib):
        score += 2
        signals.append("institution")

    if _dates_exact(a, b):
        score += 1
        signals.append("dateRange")
    elif _dates_overlap(a, b):
        score += 1
        signals.append("dateRange-overlap")

    return score, tuple(signals)


_SCORERS: dict[str, Any] = {
    "experiences": _experience_score,
    "organizations": _organization_score,
    "skills": _skill_score,
    "education": _education_score,
}

EVIDENCE_MATCHED_TYPES: frozenset[str] = frozenset(_SCORERS)


def match_entities(
    entity_type: str,
    left_entities: Sequence[Mapping[str, Any]],
    right_entities: Sequence[Mapping[str, Any]],
    left_org_names: Mapping[str, str] | None = None,
    right_org_names: Mapping[str, str] | None = None,
) -> list[EntityEvidenceMatch]:
    """Deterministically pair entities of the same type across two profiles.

    Only entities with a ``id`` are considered. Each left entity matches at
    most one right entity (greedy, sorted order); each right entity is used at
    most once. Returns ``EntityEvidenceMatch`` objects with the evidence
    signals that justify each match.
    """
    scorer = _SCORERS[entity_type]
    left_by_id = {
        str(e["id"]): e for e in left_entities if isinstance(e, Mapping) and e.get("id")
    }
    right_by_id = {
        str(e["id"]): e for e in right_entities if isinstance(e, Mapping) and e.get("id")
    }
    left_org_names = left_org_names or {}
    right_org_names = right_org_names or {}

    matches: list[EntityEvidenceMatch] = []
    used_right: set[str] = set()

    for left_id in sorted(left_by_id):
        candidates: list[tuple[int, str, tuple[str, ...]]] = []
        for right_id in sorted(right_by_id):
            if right_id in used_right:
                continue
            score, signals = scorer(
                left_by_id[left_id],
                right_by_id[right_id],
                left_org_names,
                right_org_names,
            )
            if score >= 2:
                candidates.append((score, right_id, signals))
        if not candidates:
            continue
        _, best_right, best_signals = max(candidates, key=lambda c: (c[0], c[1]))
        used_right.add(best_right)
        matches.append(EntityEvidenceMatch(entity_type, left_id, best_right, best_signals))

    return matches
