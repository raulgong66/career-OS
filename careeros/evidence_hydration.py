"""Evidence hydration for CareerOS canonical profiles.

Hydrates the top-level ``profile["evidence"]`` collection from evidence that is
already embedded in the profile:

- ``skill.extensions.experienceEvidence`` — the source skill-to-experience
  links that substantiate a skill claim.
- ``extensions._acquisition`` — the source document provenance trace.

Two axes are preserved separately on every evidence item:

- ``evidence_strength`` — a float in ``[0.1, 1.0]`` plus a band label, computed
  by the same deterministic function the skill-evidence reasoning rule uses
  (more experiences, more distinct organizations, and more total years raise
  the value). Reused verbatim — no new confidence math.
- ``provenance`` — ``full`` / ``partial`` / ``none``, derived only from fields
  actually present in ``_acquisition``. Never fabricated.

``confidence_grade`` combines the two: the evidence-strength label capped by
the provenance grade (``full`` -> ``very_high``, ``partial`` -> ``high``,
``none`` -> ``medium``) so that missing provenance can never silently present a
claim as more confident than the recorded source allows.
"""

from __future__ import annotations

from typing import Any

from .knowledge import KnowledgeGraphBuilder

# Evidence-strength band labels, ordered weakest -> strongest.
BAND_ORDER = ("very_low", "low", "medium", "high", "very_high")

# Provenance grade -> the strongest confidence-grade label it permits.
PROVENANCE_CAP = {
    "full": "very_high",
    "partial": "high",
    "none": "medium",
}

# Fields that must all be present for provenance to be "full".
# Mirrors the reconciliation provenance warnings (MISSING_SOURCE_HASH,
# MISSING_SOURCE_NAME, MISSING_IMPORTED_AT).
_PROVENANCE_FIELDS = ("sourceHash", "sourceName", "importedAt")


def compute_evidence_strength(skill: dict[str, Any]) -> float:
    """Evidence-strength confidence for a collected skill entry.

    Reuses the exact semantics of SkillEvidenceStrengthRule._compute_confidence
    (bounds ``[0.1, 1.0]``).
    """
    base = 0.1
    exp_count = skill["experience_count"]
    org_count = skill["organization_count"]
    years = skill["total_years"]

    if exp_count >= 4:
        base += 0.35
    elif exp_count >= 2:
        base += 0.20
    elif exp_count >= 1:
        base += 0.10

    if org_count >= 3:
        base += 0.25
    elif org_count >= 2:
        base += 0.15
    elif org_count >= 1:
        base += 0.05

    if years >= 5.0:
        base += 0.20
    elif years >= 3.0:
        base += 0.15
    elif years >= 1.0:
        base += 0.10
    else:
        base += 0.05

    if exp_count >= 1 and org_count >= 1 and years >= 2.0:
        base += 0.10

    return round(min(base, 1.0), 2)


def evidence_strength_label(confidence: float) -> str:
    """Map an evidence-strength confidence to its band label."""
    if confidence >= 0.8:
        return "very_high"
    if confidence >= 0.6:
        return "high"
    if confidence >= 0.4:
        return "medium"
    if confidence >= 0.2:
        return "low"
    return "very_low"


def provenance_grade(acquisition: dict[str, Any] | None) -> str:
    """Classify provenance availability from the ``_acquisition`` trace.

    - ``full``: ``sourceHash``, ``sourceName`` and ``importedAt`` are all present.
    - ``partial``: an acquisition trace exists but at least one of the three
      fields is missing.
    - ``none``: no acquisition trace at all.
    """
    acq = acquisition or {}
    present = [field for field in _PROVENANCE_FIELDS if acq.get(field)]
    if len(present) == len(_PROVENANCE_FIELDS):
        return "full"
    if acq:
        return "partial"
    return "none"


def provenance_cap(provenance: str) -> str:
    """The strongest confidence-grade label a provenance grade permits."""
    return PROVENANCE_CAP.get(provenance, "medium")


def confidence_grade(strength_label: str, provenance: str) -> str:
    """Combine evidence strength and provenance into a single capped grade.

    The grade is the evidence-strength label lowered, if needed, to the
    strongest label the provenance grade permits. It never exceeds the
    evidence-strength label and never exceeds the provenance cap.
    """
    cap = provenance_cap(provenance)
    strength_index = BAND_ORDER.index(strength_label)
    cap_index = BAND_ORDER.index(cap)
    return BAND_ORDER[min(strength_index, cap_index)]


def derive_skill_evidence_confidence(
    skill_data: list[dict[str, Any]],
    profile: dict[str, Any],
) -> float:
    """Mean evidence strength across collected skills, or ``0.0`` when none.

    Kept as a plain evidence-derived float; the provenance-aware combined grade
    is exposed separately via :func:`evidence_confidence_meta`.
    """
    if not skill_data:
        return 0.0
    strengths = [compute_evidence_strength(s) for s in skill_data]
    return round(sum(strengths) / len(strengths), 2)


def evidence_confidence_meta(
    skill_data: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Provenance-aware metadata for a skill-evidence reasoning result.

    Preserves both the mean evidence strength and the provenance grade while
    exposing the combined (capped) confidence grade.
    """
    confidence = derive_skill_evidence_confidence(skill_data, profile)
    label = evidence_strength_label(confidence)
    acquisition = (profile.get("extensions") or {}).get("_acquisition") or {}
    prov = provenance_grade(acquisition)
    return {
        "evidence_strength_mean": confidence,
        "provenance": prov,
        "evidence_confidence_grade": confidence_grade(label, prov),
    }


def _provenance_explanation(provenance: str, acquisition: dict[str, Any]) -> str:
    """Human-readable provenance explanation using only recorded fields."""
    missing = [field for field in _PROVENANCE_FIELDS if not acquisition.get(field)]
    if provenance == "full":
        return "Source verified: sourceHash, sourceName, importedAt on record."
    if provenance == "partial":
        return (
            "Source document on record but unverified; missing: "
            + ", ".join(missing)
            + "."
        )
    return "No source document on record; provenance unavailable."


def _plural(count: int, singular: str, plural: str) -> str:
    """Deterministic pluralization for plain-language counts."""
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def _provenance_plain(provenance: str) -> str:
    """Plain-language provenance sentence (no internal field names)."""
    if provenance == "full":
        return "The source document has been verified."
    if provenance == "partial":
        return "The source document is on record but has not been independently verified."
    return "No source document is on record."


def _evidence_basis(
    strength_label: str,
    entry: dict[str, Any],
    provenance: str,
    acquisition: dict[str, Any],
) -> str:
    """Plain-language basis for an evidence item (strength + provenance)."""
    experiences = _plural(entry["experience_count"], "job experience", "job experiences")
    organizations = _plural(entry["organization_count"], "employer", "employers")
    strength_basis = (
        f"Supported by {experiences} across {organizations} over "
        f"{entry['total_years']} years of work."
    )
    return f"{strength_basis} {_provenance_plain(provenance)}"


def build_evidence_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Build schema-shaped evidence items from a canonical profile.

    One item is produced per ``skill.extensions.experienceEvidence`` entry.
    Deterministic: skills are iterated in profile order, then each skill's
    evidence entries in order. Idempotent: computed purely from the profile's
    skills, never reading or duplicating pre-existing evidence items.

    Only fields that actually exist are copied; no source name, hash, or import
    timestamp is ever fabricated.
    """
    # Lazy imports avoid an import cycle: skill_rules imports this module.
    from .reasoning import RuleContext
    from .reasoning.rules.skill_rules import _collect_skill_data

    acquisition = (profile.get("extensions") or {}).get("_acquisition") or {}
    prov = provenance_grade(acquisition)

    graph = KnowledgeGraphBuilder().build(profile)
    skill_data = _collect_skill_data(RuleContext(graph=graph, profile=profile))
    by_skill_id = {s["id"]: s for s in skill_data if s["id"]}

    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for skill in profile.get("skills") or []:
        skill_id = skill.get("id")
        if not skill_id:
            continue
        skill_name = skill.get("name", "")
        entry = by_skill_id.get(skill_id) or {
            "experience_count": 0,
            "organization_count": 0,
            "total_years": 0.0,
        }

        strength = compute_evidence_strength(entry)
        strength_label = evidence_strength_label(strength)
        grade = confidence_grade(strength_label, prov)
        basis = _evidence_basis(strength_label, entry, prov, acquisition)

        for ev in (skill.get("extensions") or {}).get("experienceEvidence") or []:
            exp_id = ev.get("experienceId")
            if not exp_id:
                continue
            item_id = f"evidence-{skill_id}-{exp_id}"
            if item_id in seen:
                continue
            seen.add(item_id)

            exp_title = ev.get("title") or ""
            organization = ev.get("organization") or ""
            if not exp_title:
                for exp in profile.get("experiences") or []:
                    if exp.get("id") == exp_id and exp.get("title"):
                        exp_title = exp["title"]
                        break

            items.append({
                "id": item_id,
                "title": (
                    f"{exp_title} - {skill_name}"
                    if exp_title
                    else f"{skill_name} (experience evidence)"
                ),
                "description": basis,
                "evidenceType": "experience",
                "relatedRefs": [
                    {"id": skill_id, "type": "skill"},
                    {"id": exp_id, "type": "experience"},
                ],
                "extensions": {
                    "skillId": skill_id,
                    "skillName": skill_name,
                    "experienceId": exp_id,
                    "experienceTitle": exp_title,
                    "organization": organization,
                    "evidenceStrength": strength,
                    "evidenceStrengthLabel": strength_label,
                    "provenance": prov,
                    "provenanceExplanation": _provenance_explanation(
                        prov, acquisition
                    ),
                    "confidenceGrade": grade,
                    "basis": basis,
                },
            })

    return items
