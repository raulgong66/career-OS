"""Focused tests for rehearsal fixes 1 and 3 (matching + partner output)."""

import yaml

from careeros.optimizer import CVOptimizer, OptimizationStatus
from careeros.reporting import (
    band_label,
    evidence_backed_coverage,
    provenance_label,
    render_candidate_assessment,
)
from careeros.reporting.partner_output import (
    jd_concepts_from_text,
    render_evidence_item,
)


# ---------------------------------------------------------------------------
# Fix 1: capitalized-sequence phrases must not hide single-word requirements
# ---------------------------------------------------------------------------


def test_capitalized_sequence_phrase_surfaces_single_word_components() -> None:
    requirements = CVOptimizer._extract_requirements(
        "AWS Cloud Platform Expert exp-capgemini Capgemini Senior Engineer"
    )
    assert "aws cloud platform expert" in requirements
    assert "amazon web services" in requirements
    assert "cloud" in requirements


def test_capitalized_sequence_phrase_resolves_to_cloud_platform_concept() -> None:
    optimizer = CVOptimizer({})
    concepts = optimizer._element_concepts({"id": "s1", "name": "AWS Cloud Platform Expert"})
    assert "cloud-platform" in concepts


def test_aws_skill_matches_cloud_migration_jd() -> None:
    optimizer = CVOptimizer({})
    element_concepts = optimizer._element_concepts({"id": "s1", "name": "AWS Cloud Platform Expert"})
    jd_concepts = jd_concepts_from_text("AWS cloud migration with DevSecOps security framework")
    assert "cloud-platform" in jd_concepts
    assert "cloud-platform" in element_concepts
    assert jd_concepts & element_concepts


# ---------------------------------------------------------------------------
# Fix 2: separated text-match vs evidence-backed coverage
# ---------------------------------------------------------------------------


def _minimal_profile() -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-test",
            "names": [{"value": "Test Candidate", "usage": "professional"}],
        },
        "skills": [
            {"id": "s1", "name": "AWS Cloud Platform Expert"},
        ],
        "artifacts": [
            {"id": "cv-min", "artifactType": "CV", "sourceRefs": []},
        ],
    }


def test_text_match_coverage_and_evidence_backed_coverage_are_separated() -> None:
    profile = _minimal_profile()
    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv("cv-min", "AWS cloud migration")

    assert result.summary is not None
    assert result.summary.requirement_coverage == 100.0

    jd_concepts = jd_concepts_from_text("AWS cloud migration")
    assert jd_concepts == {"cloud-platform"}
    assert evidence_backed_coverage(optimizer, jd_concepts) == 0.0


def test_partner_output_renders_separated_coverage_with_qualifier() -> None:
    profile = _minimal_profile()
    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv("cv-min", "AWS cloud migration")

    out = render_candidate_assessment(profile, "AWS cloud migration", result)

    lines = out.splitlines()
    text_line = next(i for i, l in enumerate(lines) if l.startswith("  Text match:"))
    ev_line = next(i for i, l in enumerate(lines) if l.startswith("  Evidence-backed:"))
    assert lines[text_line].endswith("100%")
    assert lines[ev_line].endswith("0%")
    assert lines[text_line].index("100%") == lines[ev_line].index("0%")
    assert (
        "Required capabilities are referenced in this profile but are not "
        "supported by evidence-backed records." in out
    )
    assert "Overall profile" not in out


# ---------------------------------------------------------------------------
# Fix 3A: human-readable partner labels
# ---------------------------------------------------------------------------


def test_band_labels_map_to_human_readable_values() -> None:
    assert band_label("very_high") == "Very high"
    assert band_label("high") == "High"
    assert band_label("medium") == "Medium"
    assert band_label("low") == "Low"
    assert band_label("very_low") == "Very low"


def test_provenance_labels_map_to_source_verification_statements() -> None:
    assert provenance_label("full") == "Verified from source document"
    assert provenance_label("partial") == "On record - not independently verified"
    assert provenance_label("none") == "No source document on record"


# ---------------------------------------------------------------------------
# Fix 3B: confidence and source verification rendered adjacently
# ---------------------------------------------------------------------------


def test_evidence_item_renders_confidence_and_source_verification_adjacent() -> None:
    evidence = {
        "id": "evidence-1",
        "evidenceType": "experience",
        "description": "Senior Engineer at Capgemini",
        "extensions": {
            "evidenceStrengthLabel": "medium",
            "confidenceGrade": "medium",
            "provenance": "partial",
            "basis": "Supported by 1 job experience across 1 employer over 11.95 years.",
        },
    }

    out = render_evidence_item(evidence)

    assert "Evidence strength:     Medium" in out
    assert "Confidence:            Medium" in out
    assert "Source verification:   On record - not independently verified" in out
    confidence_idx = out.index("Confidence:")
    source_line_start = out.index("\n", confidence_idx) + 1
    assert out[source_line_start:].startswith("    Source verification:")


# ---------------------------------------------------------------------------
# Conditional coverage qualification note
# ---------------------------------------------------------------------------

_JD = (
    "AWS cloud migration with DevSecOps security framework for a regulated financial "
    "services client. Cloud Migration Lead: AWS production migration experience, "
    "architecture design, client-facing, financial sector. DevSecOps Engineer: "
    "DevSecOps security framework implementation, Zero Trust, Kubernetes, compliance "
    "in regulated environment. Cloud Engineer: AWS operational experience, CI/CD "
    "pipelines, Docker, Linux."
)

_NOTE = "\n".join(
    f"  {line}"
    for line in [
        "Note: Coverage reflects concept-level evidence matches.",
        "This candidate does not have an evidence-backed recommendation",
        "for the Cloud Migration Lead AWS requirement.",
        "See capability detail below.",
    ]
)


def _ev(id: str) -> dict:
    return {
        "id": id,
        "evidenceType": "experience",
        "description": f"Worked as {id}",
        "extensions": {
            "evidenceStrengthLabel": "high",
            "confidenceGrade": "high",
            "provenance": "partial",
            "basis": "Supported by job experiences.",
        },
    }


def _profiled_candidate(experiences: list[dict]) -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-test",
            "names": [{"value": "Test Candidate", "usage": "professional"}],
        },
        "experiences": experiences,
        "organizations": [{"id": "org-1", "name": "ACME Corp"}],
        "evidence": [_ev("evidence-1")],
        "artifacts": [{"id": "cv-min", "artifactType": "CV", "sourceRefs": []}],
    }


def _experience(title: str, scope: str) -> dict:
    return {
        "id": "e1",
        "title": title,
        "scope": scope,
        "organizationRefs": [{"id": "org-1", "type": "organization"}],
        "evidenceRefs": [{"id": "evidence-1", "type": "experience"}],
    }


def _render(title: str, scope: str) -> str:
    profile = _profiled_candidate([_experience(title, scope)])
    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv("cv-min", _JD)
    return render_candidate_assessment(profile, _JD, result)


def test_primary_role_phrase_derived_from_jd() -> None:
    from careeros.reporting.partner_output import primary_role_phrase

    assert primary_role_phrase(_JD) == "cloud migration"


def test_note_appears_when_high_coverage_without_primary_role_recommendation() -> None:
    # Raul-like: evidence-backed coverage >= 50% (AWS/K8s/CI-CD scope) but the
    # evidence-backed element never addresses the Cloud Migration Lead role.
    out = _render(
        "Senior Engineer",
        "AWS, Kubernetes, Docker, CI/CD, DevSecOps, network security at ACME Corp",
    )
    assert _NOTE in out


def test_note_absent_when_primary_role_recommendation_exists() -> None:
    # Marcus-like: an evidence-backed element addresses the Cloud Migration
    # Lead role, so the note must not appear.
    out = _render(
        "Lead Cloud Migration Architect",
        "AWS, Kubernetes, Docker, CI/CD, DevSecOps, network security at ACME Corp",
    )
    assert _NOTE not in out


def test_note_absent_when_coverage_below_threshold() -> None:
    # Roshan-like: evidence-backed coverage is below 50%, so the note must not
    # appear even though no primary-role recommendation exists.
    out = _render("Senior Engineer", "Python development at ACME Corp")
    assert _NOTE not in out
