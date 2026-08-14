from __future__ import annotations

import re
import unicodedata

COMPANY_ABBREVIATIONS: dict[str, str] = {
    "international business machines": "ibm",
}


def normalize_company(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return COMPANY_ABBREVIATIONS.get(normalized, normalized)


_DATE_REPLACE_MAP: dict[str, str] = {
    "present": "",
    "now": "",
    "current": "",
    "ongoing": "",
}


def normalize_date(date_str: str) -> str:
    date_str = date_str.strip()
    date_lower = date_str.lower()
    date_str = _DATE_REPLACE_MAP.get(date_lower, date_str)
    date_str = re.sub(r"\s+", " ", date_str).strip()
    return date_str


def person_id_from_name(name: str) -> str:
    """Derive a deterministic ``person-*`` id from a person's display name.

    Follows the documented profile-id contract (lowercase, spaces become
    hyphens, non-alphanumerics dropped) and folds non-ASCII letters to their
    ASCII equivalents (e.g. ``González`` -> ``gonzalez``). Returns an empty
    string when no usable id can be derived.
    """
    folded = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_lower = "".join(ch for ch in folded if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_lower).strip("-")
    return f"person-{slug}" if slug else ""


def extract_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    match = re.search(r"(\d{4})", date_str)
    return int(match.group(1)) if match else None


_MONTH_MAP: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def extract_month(date_str: str | None) -> int | None:
    if not date_str:
        return None
    for abbr, num in _MONTH_MAP.items():
        if abbr in date_str.lower():
            return num
    return None
