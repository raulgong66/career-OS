"""Deterministic duplicate-narrative suppression for tailored CVs.

Suppresses redundant narrative fields in the generator input of a tailored CV
(an ``ExportContract``) without ever touching the canonical profile. Comparison
uses the exact M1.25 narrative normalization shared with the profile-quality
layer (``reasoning.rules.recommendation_rules._normalize_narrative``), so the
tailoring layer and the duplicate-narrative detection layer compare narrative
the same way.

Deterministic rules:

- Subset/superset: a narrative field whose entire normalized text is contained
  in another selected narrative is redundant. A professional summary is only
  suppressed when contained in another professional summary (the summary
  section is the canonical home for profile-level narrative); an experience
  scope is suppressed when contained in any other selected narrative.
- Exact duplicates: among fields with identical normalized text, the most
  appropriate representation is retained (professional summary preferred over
  experience scope; otherwise first-seen order) and the remaining duplicates
  are suppressed.

Suppressed experience scopes leave the experience entry intact (title, dates,
and provenance refs are preserved); duplicate professional summaries are
dropped from the source list. All other sources keep their order and
provenance.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .export_contract import ExportContract, ExportSource
from .reasoning.rules.recommendation_rules import _normalize_narrative

_NARRATIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "professional_summary": ("text", "label"),
    "experience": ("scope",),
}


def _narrative_segments(sources: list[ExportSource]) -> list[dict[str, Any]]:
    """Collect narrative segments from export sources in source order."""
    segments: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        keys = _NARRATIVE_FIELDS.get(source.type.lower())
        if not keys:
            continue
        text = ""
        for key in keys:
            value = source.data.get(key)
            if value:
                text = str(value)
                break
        text = text.strip()
        if text:
            segments.append(
                {
                    "index": index,
                    "type": source.type.lower(),
                    "normalized": _normalize_narrative(text),
                }
            )
    return segments


def _redundant_indices(segments: list[dict[str, Any]]) -> set[int]:
    """Return the indices of redundant narrative segments, deterministically."""
    redundant: set[int] = set()

    for seg_a in segments:
        if seg_a["index"] in redundant:
            continue
        for seg_b in segments:
            if seg_a["index"] == seg_b["index"] or seg_b["index"] in redundant:
                continue
            if seg_a["normalized"] == seg_b["normalized"]:
                continue
            if seg_a["normalized"] not in seg_b["normalized"]:
                continue
            if seg_a["type"] == "professional_summary" and seg_b["type"] != "professional_summary":
                continue
            redundant.add(seg_a["index"])
            break

    groups: dict[str, list[dict[str, Any]]] = {}
    for seg in segments:
        if seg["index"] in redundant:
            continue
        groups.setdefault(seg["normalized"], []).append(seg)

    for group in groups.values():
        if len(group) < 2:
            continue
        summaries = [seg for seg in group if seg["type"] == "professional_summary"]
        keeper = summaries[0] if summaries else group[0]
        for seg in group:
            if seg is not keeper:
                redundant.add(seg["index"])

    return redundant


def suppress_duplicate_narrative(contract: ExportContract) -> ExportContract:
    """Return a copy of the contract with redundant narrative suppressed.

    Operates only on the in-memory contract used to generate the tailored
    artifact; the canonical profile is never modified.

    Args:
        contract: The export contract for the tailored artifact.

    Returns:
        A new contract with redundant narrative suppressed. All other sources,
        their order, and their provenance refs are preserved.
    """
    if not contract.sources:
        return contract

    segments = _narrative_segments(contract.sources)
    if len(segments) < 2:
        return contract

    redundant = _redundant_indices(segments)
    if not redundant:
        return contract

    sources: list[ExportSource] = []
    for index, source in enumerate(contract.sources):
        if index not in redundant:
            sources.append(source)
            continue
        if source.type.lower() == "professional_summary":
            continue
        data = dict(source.data)
        data.pop("scope", None)
        sources.append(
            ExportSource(type=source.type, id=source.id, data=data, ref=source.ref)
        )

    return replace(contract, sources=sources)
