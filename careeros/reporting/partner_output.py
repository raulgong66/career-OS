"""Partner-facing rendering of candidate assessments against a requirement.

This module implements the presentation-layer fixes approved by the
Commercial Advisor (rehearsal only):

1. Requirement coverage is presented as separated values so text-level
   matches can never be read as evidence-backed qualification.
2. Internal band labels are mapped to human-readable partner labels
   (Evidence strength, Confidence, Overall match score, Requirement
   match, Source verification).
3. Confidence and source verification are rendered adjacently for each
   evidence item.
4. The aggregate profile-level confidence grade is not rendered in
   partner-facing output.
5. A conditional plain-language note is rendered next to the coverage
   metrics when coverage looks strong but the candidate has no
   evidence-backed recommendation for the primary role requirement.

All values are derived from the optimizer's existing computation; no
scoring, coverage, or provenance model changes are made here.
"""

from __future__ import annotations

from typing import Any

from ..optimizer import (
    CVOptimizer,
    _CAPITALIZED_SEQUENCE_RE,
    _SEQUENCE_BLACKLIST,
    _STOP_WORDS,
)

_BAND_LABELS: dict[str, str] = {
    "very_high": "Very high",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "very_low": "Very low",
}

_PROVENANCE_LABELS: dict[str, str] = {
    "full": "Verified from source document",
    "partial": "On record - not independently verified",
    "none": "No source document on record",
}

# Categories iterated for concept / evidence coverage, mirroring the
# optimizer's own element iteration in ``_compute_summary``.
_ELEMENT_TYPES: dict[str, str] = {
    "skills": "skill",
    "experiences": "experience",
    "projects": "project",
    "achievements": "achievement",
    "certifications": "certification",
    "education": "education",
}

_UNEVIDENCED_TEXT = (
    "Required capabilities are referenced in this profile but are not "
    "supported by evidence-backed records. CareerOS cannot produce an "
    "evidence-backed recommendation for this candidate against this requirement."
)

# Conditional qualification note.  Shown only when coverage looks strong
# yet no evidence-backed recommendation addresses the primary role
# requirement (see ``render_coverage_block``).
_PRIMARY_ROLE_NOTE = [
    "Note: Coverage reflects concept-level evidence matches.",
    "This candidate does not have an evidence-backed recommendation",
    "for the Cloud Migration Lead AWS requirement.",
    "See capability detail below.",
]

# Coverage threshold above which the conditional note can be shown.
_PRIMARY_ROLE_NOTE_MIN_COVERAGE = 50.0


def band_label(band: str) -> str:
    """Map an internal band label to a human-readable partner label."""
    if not band:
        return band
    return _BAND_LABELS.get(band, band.replace("_", " ").title())


def provenance_label(grade: str) -> str:
    """Map a provenance grade to a partner-facing source verification statement."""
    return _PROVENANCE_LABELS.get(grade, grade)


def jd_concepts_from_text(job_description: str) -> set[str]:
    """Resolve a job description to its canonical requirement concepts."""
    if not job_description:
        return set()
    requirements = CVOptimizer._extract_requirements(job_description)
    return CVOptimizer._resolve_concepts(requirements)


def evidence_backed_concepts(optimizer: CVOptimizer) -> set[str]:
    """Concept IDs matched by profile elements that have backing evidence.

    Presentation-side derivation for the evidence-backed coverage value.
    Reuses the optimizer's existing element-concept and backing-evidence
    logic; no optimizer computation is changed.
    """
    matched: set[str] = set()
    for list_key, type_name in _ELEMENT_TYPES.items():
        for element in optimizer.profile.get(list_key, []) or []:
            if optimizer._get_backing_evidence(element, type_name):
                matched.update(optimizer._element_concepts(element))
    return matched


def evidence_backed_coverage(optimizer: CVOptimizer, jd_concepts: set[str]) -> float:
    """Percentage of JD concepts matched by evidence-backed elements."""
    if not jd_concepts:
        return 0.0
    matched = evidence_backed_concepts(optimizer) & jd_concepts
    return len(matched) / len(jd_concepts) * 100.0


def primary_role_phrase(job_description: str) -> str:
    """Derive the primary (lead) role requirement phrase from the JD.

    The primary role is taken to be the first capitalized multi-word
    sequence in the job description (the lead role header, e.g. "Cloud
    Migration Lead").  Role-title stop words (e.g. "lead") are dropped so
    the phrase matches both "Cloud Migration Lead" and "Lead Cloud
    Migration Architect".  Returns "" when no such phrase exists.
    """
    if not job_description:
        return ""
    match = _CAPITALIZED_SEQUENCE_RE.search(job_description)
    if not match:
        return ""
    words = [
        word
        for word in match.group().lower().split()
        if word not in _STOP_WORDS and word not in _SEQUENCE_BLACKLIST
    ]
    return " ".join(words)


def has_primary_role_recommendation(
    optimizer: CVOptimizer,
    result: Any,
    job_description: str,
) -> bool:
    """True when an evidence-backed recommendation addresses the primary role.

    A recommendation addresses the primary role when its recommended
    element's text contains the primary-role requirement phrase derived
    from the job description.  Presentation-side only; recommendations
    and their evidence are not modified.
    """
    phrase = primary_role_phrase(job_description)
    if not phrase:
        return False
    for rec in result.recommendations or []:
        element_text = optimizer._collect_element_text(rec.details).lower()
        if phrase in element_text:
            return True
    return False


def render_coverage_block(
    summary: Any,
    optimizer: CVOptimizer,
    jd_concepts: set[str],
    result: Any,
    job_description: str,
) -> str:
    """Render the requirement-coverage block with separated values.

    The conditional qualification note is added when evidence-backed
    coverage is at or above 50% but no evidence-backed recommendation
    addresses the primary role requirement.  The note is a presentation
    aid only; coverage and recommendation calculations are unchanged.
    """
    text_coverage = round(summary.requirement_coverage or 0.0, 1)
    ev_backed_coverage = round(evidence_backed_coverage(optimizer, jd_concepts), 1)

    lines = ["Profile coverage:"]
    lines.append(f"  Text match:              {text_coverage:g}%")
    lines.append(f"  Evidence-backed:         {ev_backed_coverage:g}%")
    if ev_backed_coverage < text_coverage:
        lines.append(f"  {_UNEVIDENCED_TEXT}")

    if (
        ev_backed_coverage >= _PRIMARY_ROLE_NOTE_MIN_COVERAGE
        and not has_primary_role_recommendation(optimizer, result, job_description)
    ):
        lines.append("")
        lines.extend(f"  {line}" for line in _PRIMARY_ROLE_NOTE)

    return "\n".join(lines)


def render_evidence_item(evidence: dict[str, Any]) -> str:
    """Render a single evidence item with partner-facing labels."""
    ext = evidence.get("extensions") or {}
    kind = evidence.get("evidenceType", "evidence")
    description = evidence.get("description") or evidence.get("title") or evidence.get("id", "?")
    lines = [f"  - Evidence: {kind} | {description}"]
    strength = ext.get("evidenceStrengthLabel", "")
    confidence = ext.get("confidenceGrade", "")
    provenance = ext.get("provenance", "")
    basis = ext.get("basis")
    lines.append(f"    Evidence strength:     {band_label(strength)}")
    lines.append(f"    Confidence:            {band_label(confidence)}")
    lines.append(f"    Source verification:   {provenance_label(provenance)}")
    if basis:
        lines.append(f"    Basis:                 {basis}")
    return "\n".join(lines)


def render_recommendation(rec: Any) -> str:
    """Render one optimizer recommendation with partner-facing labels.

    The aggregate profile-level confidence grade is intentionally not
    rendered here; only per-evidence Confidence values appear.
    """
    scores = rec.scores or {}
    lines = [f"{rec.display_name}  ({rec.type} - {rec.operation})"]
    lines.append(f"  Overall match score:   {scores.get('weighted_total', 0.0):.2f}")
    lines.append(
        f"  Requirement match:     {scores.get('job_description_match', 0.0):.1f}  "
        f"Context match: {scores.get('target_context_match', 0.0):.1f}"
    )
    for evidence in rec.evidence or []:
        lines.append(render_evidence_item(evidence))
    return "\n".join(lines)


def render_candidate_assessment(profile: dict[str, Any], job_description: str, result: Any) -> str:
    """Render the full partner-facing candidate assessment.

    Suppresses the aggregate profile-level confidence grade (presentation
    only; the underlying calculation is unchanged).
    """
    names = (profile.get("person") or {}).get("names") or []
    candidate = names[0].get("value") if names else profile.get("id", "Candidate")

    lines = [f"### Candidate: {candidate}", ""]
    lines.append(f"Optimization status: {result.status.value}")
    if result.message:
        lines.append(result.message)

    if result.summary:
        lines.append("")
        lines.append(
            render_coverage_block(
                result.summary,
                CVOptimizer(profile),
                jd_concepts_from_text(job_description),
                result,
                job_description,
            )
        )

    lines.append("")
    lines.append("Evidence-backed recommendations:")
    recommendations = result.recommendations or []
    if recommendations:
        for rec in recommendations:
            lines.append("")
            lines.append(render_recommendation(rec))
    else:
        lines.append("  None.")

    return "\n".join(lines)
