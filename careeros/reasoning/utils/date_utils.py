from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DateRange:
    start: datetime | None
    end: datetime | None
    is_current: bool


def reference_now() -> datetime:
    """Return the current UTC datetime for duration calculations."""
    return datetime.now(timezone.utc)


def parse_date(s: str | None) -> datetime | None:
    """Parse partial date strings like '2022-03' or '2022' to datetime."""
    if not s:
        return None
    s = s.strip().lower()
    if s in ("present", "now", "current"):
        return None
    parts = s.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) >= 2 else 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def parse_date_range(
    dr: dict[str, Any] | None,
) -> DateRange:
    """Parse a profile dateRange dict into a DateRange."""
    if not dr:
        return DateRange(start=None, end=None, is_current=False)
    start = parse_date(dr.get("start"))
    end = parse_date(dr.get("end"))
    is_current = dr.get("isCurrent", False)
    if is_current:
        end = None
    return DateRange(start=start, end=end, is_current=is_current)


def duration_between(start: datetime, end: datetime) -> float:
    """Years between two dates as a float."""
    return (end - start).days / 365.25


def duration_years(dr: DateRange) -> float:
    """Years of a single date range. Current ranges use reference_now as end."""
    if dr.start is None:
        return 0.0
    end_dt = dr.end if dr.end is not None else reference_now()
    return duration_between(dr.start, end_dt)


def periods_overlap(a: DateRange, b: DateRange) -> bool:
    """Return True if two date ranges overlap."""
    if a.start is None or b.start is None:
        return False
    a_end = a.end if a.end is not None else reference_now()
    b_end = b.end if b.end is not None else reference_now()
    return a.start <= b_end and b.start <= a_end


def merge_overlapping_periods(periods: list[DateRange]) -> list[DateRange]:
    """Merge overlapping date ranges into a minimal set of non-overlapping ranges."""
    if not periods:
        return []
    valid = [p for p in periods if p.start is not None]
    if not valid:
        return []
    valid = sorted(valid, key=lambda p: p.start)  # type: ignore[arg-type]
    merged: list[DateRange] = []
    merged.append(valid[0])
    for p in valid[1:]:
        last = merged[-1]
        last_end = last.end if last.end is not None else reference_now()
        p_end = p.end if p.end is not None else reference_now()
        if p.start <= last_end:
            new_end = max(last_end, p_end)
            merged[-1] = DateRange(
                start=last.start,
                end=None if (last.is_current or p.is_current) else new_end,
                is_current=last.is_current or p.is_current,
            )
        else:
            merged.append(p)
    return merged


def total_experience_years(experiences: list[dict[str, Any]]) -> float:
    """Compute total professional experience years, handling overlaps."""
    periods: list[DateRange] = []
    for exp in experiences:
        dr = parse_date_range(exp.get("dateRange"))
        periods.append(dr)
    merged = merge_overlapping_periods(periods)
    return sum(duration_years(p) for p in merged)


def gap_days_between(earlier: DateRange, later: DateRange) -> int | None:
    """Days between the end of earlier and the start of later. Returns None if either has no valid end/start."""
    earlier_end = earlier.end
    later_start = later.start
    if earlier_end is None or later_start is None:
        return None
    delta = later_start - earlier_end
    return max(0, delta.days)


def employment_gaps(
    experiences: list[dict[str, Any]],
    min_gap_days: int = 30,
) -> list[dict[str, Any]]:
    """Detect employment gaps longer than min_gap_days.

    Returns sorted list of gap dicts with start, end, and duration_days.
    """
    if not experiences:
        return []
    with_dates: list[tuple[datetime, dict[str, Any]]] = []
    for exp in experiences:
        dr = parse_date_range(exp.get("dateRange"))
        if dr.start is not None:
            with_dates.append((dr.start, exp))
    with_dates.sort(key=lambda x: x[0])

    gaps: list[dict[str, Any]] = []
    prev_end: datetime | None = None
    for start_dt, exp in with_dates:
        if prev_end is not None:
            gap = (start_dt - prev_end).days
            if gap > min_gap_days:
                gaps.append(
                    {
                        "start_date": prev_end.isoformat(),
                        "end_date": start_dt.isoformat(),
                        "duration_days": gap,
                        "formatted": format_duration(gap / 365.25),
                    }
                )
        dr = parse_date_range(exp.get("dateRange"))
        if dr.end is not None:
            prev_end = dr.end
        elif dr.is_current:
            prev_end = None
        else:
            prev_end = start_dt
    return gaps


def format_duration(years: float) -> str:
    """Format a fractional year count into a human string like '3 years 6 months'."""
    total_months = round(years * 12)
    y = total_months // 12
    m = total_months % 12
    parts: list[str] = []
    if y > 0:
        parts.append(f"{y} year{'s' if y != 1 else ''}")
    if m > 0:
        parts.append(f"{m} month{'s' if m != 1 else ''}")
    return " ".join(parts) if parts else "0 months"


TITLE_LEVELS: list[tuple[tuple[str, ...], int]] = [
    (("cxo", "ceo", "cto", "cfo", "chief", "vp", "vice president"), 5),
    (("director", "head of", "principal"), 4),
    (("senior", "lead", "staff", "architect", "manager", "managing"), 3),
    (("mid", "intermediate"), 2),
    (("junior", "associate", "graduate", "intern", "trainee"), 1),
]


def _word_boundary(word: str, text: str) -> bool:
    """Check if *word* appears as a whole word (not as substring) in *text*."""
    if " " in word:
        return word in text
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def title_level(title: str) -> int:
    """Determine a numeric seniority level from a job title using keyword matching."""
    lower = title.lower()
    junior_keywords = ("junior", "associate", "graduate", "intern", "trainee")
    if any(_word_boundary(kw, lower) for kw in junior_keywords):
        level = 1
    else:
        level = 2
    for keywords, lvl in TITLE_LEVELS:
        if lvl <= 2:
            continue
        for kw in keywords:
            if _word_boundary(kw, lower):
                level = max(level, lvl)
    return level
