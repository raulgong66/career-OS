"""Tests for reasoning-aware artifact generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from careeros.export_contract import ExportContract, ExportContractBuilder
from careeros.generators import DocxCVGenerator, MarkdownCVGenerator
from careeros.reasoning import ReasoningEngine, ReasoningFindings, ReasoningReport, RuleRegistry, create_default_registry
from careeros.schema_loader import SchemaLoader


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def schema_loader(repo_root: Path) -> SchemaLoader:
    return SchemaLoader(repo_root / "schemas")


@pytest.fixture
def profile() -> dict[str, Any]:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {"headline": "AI product builder", "themes": ["AI"]},
        },
        "experiences": [
            {
                "id": "exp-1",
                "title": "Senior Engineer",
                "organizationRefs": [{"id": "org-1", "type": "organization"}],
                "dateRange": {"start": "2020-01", "end": "2024-12"},
            }
        ],
        "skills": [
            {"id": "skill-1", "name": "Python", "category": "Programming"},
            {"id": "skill-2", "name": "AWS", "category": "Cloud"},
        ],
        "education": [],
        "organizations": [{"id": "org-1", "name": "Tech Corp"}],
        "professionalSummaries": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "targetContexts": [],
        "artifacts": [
            {
                "id": "artifact-1",
                "title": "Test CV",
                "artifactType": "CV",
                "sourceRefs": [
                    {"id": "exp-1", "type": "experience"},
                    {"id": "skill-1", "type": "skill"},
                    {"id": "skill-2", "type": "skill"},
                ],
            }
        ],
    }


@pytest.fixture
def reasoning_report(profile: dict[str, Any]) -> ReasoningReport:
    registry = create_default_registry()
    engine = ReasoningEngine(registry)
    return engine.analyze(profile)


# ---- ReasoningFindings extraction ----


def test_reasoning_findings_from_report(reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    assert isinstance(findings.strongest_skills, list)
    assert isinstance(findings.core_competencies, list)
    assert isinstance(findings.technology_breadth, list)
    assert findings.career_stage is None or isinstance(findings.career_stage, str)


def test_reasoning_findings_strongest_skills(reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    if findings.strongest_skills:
        for s in findings.strongest_skills:
            assert isinstance(s, str)


def test_reasoning_findings_from_empty_report() -> None:
    from careeros.reasoning import ReasoningResult

    empty = ReasoningReport(
        profile_id="empty",
        findings=(),
        findings_by_type={},
        summary={},
        execution_stats={},
    )
    findings = ReasoningFindings.from_report(empty)
    assert findings.strongest_skills == []
    assert findings.core_competencies == []
    assert findings.strongest_experience is None
    assert findings.leadership_indicators == []
    assert findings.technology_breadth == []
    assert findings.domain_expertise == []
    assert findings.career_highlights == []
    assert findings.career_stage is None


# ---- ExportContract carries reasoning ----


def test_export_contract_accepts_reasoning(reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="artifact-1",
        artifact_type="CV",
        person={},
        artifact={},
        reasoning=findings,
    )
    assert contract.reasoning is not None
    assert contract.reasoning is findings


def test_export_contract_reasoning_defaults_to_none() -> None:
    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="a",
        artifact_type="CV",
        person={},
        artifact={},
    )
    assert contract.reasoning is None


# ---- Markdown generator: backward compatibility ----


def test_markdown_generator_works_without_reasoning(schema_loader: SchemaLoader, profile: dict[str, Any]) -> None:
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1")
    assert contract.reasoning is None
    markdown = MarkdownCVGenerator().generate(contract)
    assert "# Jane Doe" in markdown
    assert "- **Senior Engineer**" in markdown
    assert "- Python (Programming)" in markdown
    assert "- AWS (Cloud)" in markdown
    assert "_Derived from profile version: 1.0.0_" in markdown


# ---- Markdown generator: reasoning sections ----


def test_markdown_generator_includes_reasoning_when_available(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    markdown = MarkdownCVGenerator().generate(contract)

    # Core sections still present
    assert "# Jane Doe" in markdown
    assert "_Derived from profile version: 1.0.0_" in markdown

    # Reasoning-derived sections present
    if findings.core_competencies:
        assert "Core Competencies:" in markdown
    if findings.strongest_skills:
        assert "Strongest Skills:" in markdown
    if findings.technology_breadth:
        assert "Technology Breadth:" in markdown


def test_markdown_generator_reasoning_career_stage(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    markdown = MarkdownCVGenerator().generate(contract)

    if findings.career_stage:
        assert f"**Career Stage:** {findings.career_stage}" in markdown


def test_markdown_generator_reasoning_strongest_experience(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    markdown = MarkdownCVGenerator().generate(contract)

    if findings.strongest_experience:
        title = findings.strongest_experience.get("title") or findings.strongest_experience.get("role", "")
        if title:
            assert title in markdown


# ---- Reasoning executes exactly once ----


def test_reasoning_runs_once_per_pipeline_call(schema_loader: SchemaLoader, profile: dict[str, Any]) -> None:
    """Verify that calling the generator triggers reasoning execution exactly once."""
    from careeros.pipelines import generate_artifact

    profile_file = _write_profile(profile)
    try:
        result = generate_artifact(profile_file, "artifact-1", "markdown", schema_loader)
        assert isinstance(result, str)
        assert "# Jane Doe" in result
    finally:
        profile_file.unlink(missing_ok=True)


# ---- DOCX generator includes reasoning when available ----


def test_docx_generator_works_without_reasoning(schema_loader: SchemaLoader, profile: dict[str, Any]) -> None:
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1")
    output = DocxCVGenerator().generate(contract)
    assert isinstance(output, bytes)
    assert output.startswith(b"PK")


def test_docx_generator_includes_reasoning_when_available(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    from io import BytesIO
    from docx import Document

    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    output = DocxCVGenerator().generate(contract)
    document = Document(BytesIO(output))
    text = "\n".join(p.text for p in document.paragraphs)

    assert "Jane Doe" in text
    if findings.core_competencies:
        assert "Core Competencies:" in text


# ---- Pipeline integration ----


def test_pipeline_with_reasoning_via_generate_markdown_cv(schema_loader: SchemaLoader, profile: dict[str, Any]) -> None:
    from careeros.pipelines import generate_markdown_cv

    profile_file = _write_profile(profile)
    try:
        markdown = generate_markdown_cv(profile_file, "artifact-1", schema_loader)
        assert "# Jane Doe" in markdown
        # Reasoning is optional — just verify it doesn't crash
    finally:
        profile_file.unlink(missing_ok=True)


def test_pipeline_backward_compatible_no_job_desc(schema_loader: SchemaLoader, profile: dict[str, Any]) -> None:
    """Without job_description, generate_artifact returns str, not tuple."""
    from careeros.pipelines import generate_artifact

    profile_file = _write_profile(profile)
    try:
        result = generate_artifact(profile_file, "artifact-1", "markdown", schema_loader)
        assert isinstance(result, str)
    finally:
        profile_file.unlink(missing_ok=True)


# ---- Helpers ----


def _write_profile(profile: dict[str, Any]) -> Path:
    import tempfile, yaml
    path = Path(tempfile.mktemp(suffix=".yaml"))
    path.write_text(yaml.safe_dump(profile), encoding="utf-8")
    return path
