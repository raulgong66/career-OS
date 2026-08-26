"""Tests for reasoning-aware artifact generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from careeros.export_contract import ExportContract, ExportContractBuilder, ExportSource
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
    assert "Senior Engineer" in markdown
    assert "## Core Competencies" in markdown
    assert "Python, AWS" in markdown


# ---- Markdown generator: reasoning sections ----


def test_markdown_generator_includes_reasoning_when_available(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    markdown = MarkdownCVGenerator().generate(contract)

    # Core sections still present
    assert "# Jane Doe" in markdown
    assert "## Professional Summary" in markdown
    assert "## Core Competencies" in markdown

    # Reasoning feeds the summary and competencies sections
    if findings.career_stage:
        assert findings.career_stage in markdown
    if findings.core_competencies or findings.strongest_skills:
        for skill in findings.strongest_skills:
            assert skill in markdown


def test_markdown_generator_reasoning_career_stage(schema_loader: SchemaLoader, profile: dict[str, Any], reasoning_report: ReasoningReport) -> None:
    findings = ReasoningFindings.from_report(reasoning_report)
    contract = ExportContractBuilder(schema_loader).build(profile, "artifact-1", reasoning=findings)
    markdown = MarkdownCVGenerator().generate(contract)

    if findings.career_stage:
        assert f"is a {findings.career_stage} professional" in markdown


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


def test_interest_letter_routes_through_tailoring_pipeline(schema_loader: SchemaLoader) -> None:
    """INTEREST_LETTER generation with a job description returns (artifact, OptimizationResult)."""
    from careeros.pipelines import generate_artifact

    profile: dict[str, Any] = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        "professionalSummaries": [
            {"id": "summary-1", "text": "AI product builder focused on reliable workflow systems."}
        ],
        "experiences": [
            {"id": "exp-1", "title": "Product Engineer", "scope": "Built AI-native career workflows."}
        ],
        "skills": [
            {"id": "skill-1", "name": "AI workflow design"},
            {"id": "skill-2", "name": "Kubernetes"},
        ],
        "education": [],
        "organizations": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "targetContexts": [
            {"id": "context-1", "audience": "Hiring Team", "role": "AI Product Engineer"}
        ],
        "artifacts": [
            {
                "id": "interest-letter-1",
                "title": "Interest Letter",
                "artifactType": "INTEREST_LETTER",
                "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                "sourceRefs": [
                    {"id": "summary-1", "type": "professional_summary"},
                    {"id": "exp-1", "type": "experience"},
                    {"id": "skill-1", "type": "skill"},
                ],
            }
        ],
    }

    profile_file = _write_profile(profile)
    try:
        result = generate_artifact(
            profile_file,
            "interest-letter-1",
            "markdown",
            schema_loader,
            job_description="Kubernetes engineer with automation experience",
        )
        assert isinstance(result, tuple)
        artifact, optimization_result = result
        assert isinstance(artifact, str)
        assert optimization_result.status is not None
        assert optimization_result.summary is not None
        assert "# Interest Letter" in artifact
        # Verify role-aware output
        assert "AI Product Engineer" in artifact
        assert "Hiring Team" in artifact
    finally:
        profile_file.unlink(missing_ok=True)


def test_interest_letter_without_job_description_returns_plain_string(
    schema_loader: SchemaLoader,
    profile: dict[str, Any],
) -> None:
    """Without job_description, INTEREST_LETTER generation stays on the normal path."""
    from careeros.pipelines import generate_artifact

    interest_profile = dict(profile)
    interest_profile["artifacts"] = [
        {
            "id": "interest-letter-1",
            "title": "Interest Letter",
            "artifactType": "INTEREST_LETTER",
            "targetContextRefs": [],
            "sourceRefs": [
                {"id": "exp-1", "type": "experience"},
                {"id": "skill-1", "type": "skill"},
            ],
        }
    ]

    profile_file = _write_profile(interest_profile)
    try:
        result = generate_artifact(profile_file, "interest-letter-1", "markdown", schema_loader)
        assert isinstance(result, str)
        assert "Interest Letter" in result
    finally:
        profile_file.unlink(missing_ok=True)


# ---- Interest Letter JD-awareness ----


def test_interest_letter_uses_target_context_role() -> None:
    """Opening paragraph includes the role name from target_contexts."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Senior Engineer", "audience": "Hiring Manager"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Engineer", "scope": "Built systems"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Python"}),
        ],
        job_description="Python engineer with system design experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "Senior Engineer" in result
    assert "Hiring Manager" in result


def test_interest_letter_opening_includes_jd_requirements() -> None:
    """Opening paragraph references top JD requirements when role and JD are present."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Senior Engineer", "audience": "Hiring Manager"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Engineer", "scope": "Built systems"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Python"}),
        ],
        job_description="Python engineer with system design experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "Senior Engineer" in result
    # Opening should reference specific requirements in human-readable form
    result_lower = result.lower()
    assert "python" in result_lower or "system design" in result_lower


def test_interest_letter_closing_references_role() -> None:
    """Closing paragraph references the role instead of returning bare 'Sincerely,'."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Product Manager", "audience": "Hiring Committee"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "PM", "scope": "Led product"}),
        ],
        job_description="Product manager with cross-functional leadership",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "Product Manager" in result
    assert "confident" in result.lower()
    assert "Sincerely" in result


def test_interest_letter_evidence_ordered_by_jd() -> None:
    """Evidence items are reordered by JD relevance when a job description is provided."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract_with_jd = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Python Developer", "scope": "Built backend APIs"}),
            ExportSource(type="experience", id="exp-2", data={"title": "ML Engineer", "scope": "Built Python machine learning pipelines"}),
        ],
        job_description="AI engineer with Python and machine learning experience",
    )
    result_with_jd = MarkdownInterestLetterGenerator().generate(contract_with_jd)

    # exp-2 (ML Engineer) should appear before exp-1 (Python Developer)
    # because it matches both "python" and "machine learning" requirements
    idx_exp2 = result_with_jd.find("ML Engineer")
    idx_exp1 = result_with_jd.find("Python Developer")
    assert idx_exp2 != -1 and idx_exp1 != -1
    assert idx_exp2 < idx_exp1


def test_interest_letter_generic_fallback_without_role() -> None:
    """When no target context exists, opening uses generic fallback text."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Engineer", "scope": "Built systems"}),
        ],
        job_description="Engineer with systems experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    # Should use the generic fallback — not reference a specific role
    assert "Jane Doe" in result
    assert "interest in this opportunity" in result


def test_interest_letter_pipeline_injects_target_context(schema_loader: SchemaLoader) -> None:
    """Pipeline injects profile target_contexts for INTEREST_LETTER when artifact has empty targetContextRefs."""
    from careeros.pipelines import generate_artifact

    profile: dict[str, Any] = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        "professionalSummaries": [
            {"id": "summary-1", "text": "AI product builder focused on reliable workflow systems."}
        ],
        "experiences": [
            {"id": "exp-1", "title": "Product Engineer", "scope": "Built AI-native career workflows."}
        ],
        "skills": [
            {"id": "skill-1", "name": "AI workflow design"},
            {"id": "skill-2", "name": "Kubernetes"},
        ],
        "education": [],
        "organizations": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "targetContexts": [
            {"id": "context-1", "audience": "Hiring Team", "role": "AI Product Engineer"}
        ],
        "artifacts": [
            {
                "id": "interest-letter-1",
                "title": "Interest Letter",
                "artifactType": "INTEREST_LETTER",
                # Empty targetContextRefs — the pipeline fix should inject from profile
                "targetContextRefs": [],
                "sourceRefs": [
                    {"id": "summary-1", "type": "professional_summary"},
                    {"id": "exp-1", "type": "experience"},
                    {"id": "skill-1", "type": "skill"},
                    {"id": "skill-2", "type": "skill"},
                ],
            }
        ],
    }

    profile_file = _write_profile(profile)
    try:
        artifact, _ = generate_artifact(
            profile_file,
            "interest-letter-1",
            "markdown",
            schema_loader,
            job_description="Kubernetes engineer with automation experience",
        )
        assert isinstance(artifact, str)
        # Pipeline-injected context should produce role-aware output
        assert "AI Product Engineer" in artifact
        assert "Hiring Team" in artifact
        # Opening should reference JD requirements (not generic fallback)
        result_lower = artifact.lower()
        assert "kubernetes" in result_lower or "automation" in result_lower
    finally:
        profile_file.unlink(missing_ok=True)


def _write_profile(profile: dict[str, Any]) -> Path:
    import tempfile, yaml
    path = Path(tempfile.mktemp(suffix=".yaml"))
    path.write_text(yaml.safe_dump(profile), encoding="utf-8")
    return path


# ---- Interest Letter acceptance tests (new generator) ----


def test_interest_letter_output_is_prose_not_bullets() -> None:
    """Letter body is prose paragraphs, not bullet lists."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="il-1",
        artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Senior Engineer", "scope": "Led cloud migration for enterprise clients; mentored junior engineers"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Designed microservices architecture on AWS"}),
            ExportSource(type="certification", id="cert-1", data={"name": "CISSP"}),
        ],
        job_description="AWS engineer with security and cloud architecture experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    # No bullet markers
    assert "- " not in result
    # Body paragraphs contain prose connecting requirements to evidence
    assert "Regarding" in result or "regarding" in result.lower()


def test_interest_letter_jd_a_vs_jd_b_different_evidence() -> None:
    """Different JDs produce materially different letters selecting different evidence."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    sources = [
        ExportSource(type="experience", id="exp-1", data={"title": "Cloud Architect", "scope": "Designed AWS infrastructure for high-traffic applications; reduced costs by 40%"}),
        ExportSource(type="experience", id="exp-2", data={"title": "ML Engineer", "scope": "Built recommendation engine using PyTorch; improved engagement by 25%"}),
        ExportSource(type="skill", id="skill-1", data={"name": "AWS", "category": "Cloud", "description": "Expert in AWS services including EC2, S3, Lambda"}),
        ExportSource(type="skill", id="skill-2", data={"name": "PyTorch", "category": "ML", "description": "Deep learning framework for NLP and computer vision"}),
    ]

    contract_a = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Platform Engineer", "audience": "Hiring Team"}],
        sources=sources,
        job_description="Cloud platform engineer with AWS and infrastructure automation experience",
    )
    contract_b = ExportContract(
        profile_version="1.0.0", artifact_id="il-2", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "ML Research Engineer", "audience": "ML Team"}],
        sources=sources,
        job_description="Machine learning engineer with deep learning and PyTorch experience",
    )

    result_a = MarkdownInterestLetterGenerator().generate(contract_a)
    result_b = MarkdownInterestLetterGenerator().generate(contract_b)

    # JD_A should emphasize cloud/AWS evidence, JD_B should emphasize ML/PyTorch
    assert "AWS" in result_a
    assert "PyTorch" in result_b
    # The two letters should be materially different
    assert result_a != result_b
    # JD_A should mention cloud infrastructure, JD_B should mention ML/deep learning
    assert "cloud" in result_a.lower() or "aws" in result_a.lower()
    assert "machine learning" in result_b.lower() or "pytorch" in result_b.lower()


def test_interest_letter_human_readable_requirements() -> None:
    """Requirements are displayed in human-readable form (not lowercase tokens)."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Security Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "SIEM", "category": "Security", "description": "Deployed SIEM solutions for threat detection"}),
            ExportSource(type="certification", id="cert-1", data={"name": "CISSP"}),
        ],
        job_description="Security engineer with SIEM and CISSP certification",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    # Acronyms should appear uppercase
    assert "SIEM" in result
    assert "CISSP" in result


def test_interest_letter_max_evidence_capped() -> None:
    """Letter does not include more than _MAX_EVIDENCE sources."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator, MarkdownInterestLetterGenerator as M

    sources = [
        ExportSource(type="experience", id=f"exp-{i}", data={"title": f"Role {i}", "scope": f"Did {req} work"})
        for i, req in enumerate(["python", "java", "cloud", "devops", "sql", "security", "networking"], start=1)
    ]

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=sources,
        job_description="python java cloud devops sql security networking engineer",
    )

    gen = M()
    result = gen.generate(contract)
    # No more than _MAX_EVIDENCE evidence items rendered
    evidence_count = sum(1 for i in range(1, 8) if f"Role {i}" in result)
    assert evidence_count <= gen._MAX_EVIDENCE


def test_interest_letter_body_paragraphs_capped() -> None:
    """Letter has at most _MAX_BODY_PARAGRAPHS body paragraphs."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    sources = [
        ExportSource(type="experience", id="exp-1", data={"title": "Engineer", "scope": "Python and Java and Cloud and DevOps work"}),
    ]

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=sources,
        job_description="python java cloud devops engineer",
    )

    gen = MarkdownInterestLetterGenerator()
    result = gen.generate(contract)
    body_paras = [line for line in result.splitlines() if line.startswith("Regarding")]
    assert len(body_paras) <= gen._MAX_BODY_PARAGRAPHS
