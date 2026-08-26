"""Shared helpers for extracting searchable text from export sources."""

from __future__ import annotations

from ..export_contract import ExportSource


def extract_source_text(source: ExportSource) -> str:
    """Extract searchable text from an export source for requirement matching.

    Returns a concatenation of the most descriptive fields for each source
    type.  The result is intended to be lowered and matched against
    requirement tokens; it is *not* suitable for display.
    """
    data = source.data
    st = source.type.lower()
    if st == "experience":
        return " ".join(
            str(v)
            for v in [
                data.get("title"),
                data.get("scope"),
                data.get("organization"),
            ]
            if v
        )
    if st == "project":
        return " ".join(
            str(v) for v in [data.get("name"), data.get("description")] if v
        )
    if st == "skill":
        return " ".join(
            str(v)
            for v in [
                data.get("name"),
                data.get("description"),
                data.get("category"),
            ]
            if v
        )
    if st == "achievement":
        return str(data.get("statement") or "")
    if st == "certification":
        return str(data.get("name") or "")
    if st == "education":
        return " ".join(
            str(v)
            for v in [
                data.get("program"),
                data.get("fieldOfStudy"),
                data.get("institution"),
            ]
            if v
        )
    return ""
