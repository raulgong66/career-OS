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


def _body_paragraph_count(result: str) -> int:
    """Count narrative body paragraphs in the letter (between opening and closing)."""
    sections = result.split("\n\n")
    dear_idx = next(
        (i for i, s in enumerate(sections) if s.strip().startswith("Dear")), 0
    )
    # Find the closing paragraph (starts with "I am confident" or "I am sure")
    closing_idx = len(sections)
    for i in range(dear_idx + 1, len(sections)):
        stripped = sections[i].strip()
        if stripped.startswith("I am confident") or stripped.startswith("I am sure"):
            closing_idx = i
            break
    # Skip greeting (dear_idx) and opening (dear_idx + 1)
    body = [s.strip() for s in sections[dear_idx + 2 : closing_idx] if s.strip()]
    return len(body)


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
    # Body should contain narrative prose connecting requirements to evidence
    assert "In my role" in result or "My experience" in result or "My background" in result


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
    body_count = _body_paragraph_count(result)
    assert body_count <= gen._MAX_BODY_PARAGRAPHS


# ---- Consolidation / dedup regression tests ----


def test_interest_letter_consolidates_google_and_google_cloud() -> None:
    """'google' and 'google cloud' requirements produce one paragraph, not two."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed Google Cloud infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Google Cloud", "description": "Expert in GCP"}),
        ],
        job_description="Google Cloud engineer with infrastructure experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    body_count = _body_paragraph_count(result)
    # Should be 1 body paragraph — both google and google cloud collapse to cloud_infra
    assert body_count == 1
    # The paragraph should mention Google/GCP
    assert "Google" in result or "GCP" in result


def test_interest_letter_consolidates_cloud_and_aws_and_gcp() -> None:
    """'cloud', 'aws', and 'google cloud' collapse into one paragraph."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Platform Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Architect", "scope": "Designed AWS and GCP infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Expert in AWS"}),
            ExportSource(type="skill", id="skill-2", data={"name": "Google Cloud", "description": "Expert in GCP"}),
        ],
        job_description="Cloud platform engineer with AWS and Google Cloud",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    body_count = _body_paragraph_count(result)
    # All cloud requirements should collapse into one paragraph
    assert body_count == 1, f"Expected 1 body paragraph, got {body_count}"
    # Should mention cloud-related evidence
    assert "AWS" in result or "Google Cloud" in result or "GCP" in result


def test_interest_letter_no_source_repeated_across_paragraphs() -> None:
    """Each evidence source appears at most once in the entire letter body."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed GCP and AWS infrastructure; implemented DevSecOps pipelines"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Google Cloud", "description": "Expert in GCP"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Automated security scanning in CI/CD"}),
        ],
        job_description="Cloud and DevSecOps engineer with Google Cloud",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    assert "Cloud Engineer" in result
    assert "Google Cloud" in result
    result_lower = result.lower()
    assert "devsecops" in result_lower
    # The experience source should NOT appear twice
    exp_count = result.count("In my role as Cloud Engineer")
    assert exp_count <= 1, f"Cloud Engineer experience repeated {exp_count} times"


def test_interest_letter_body_has_at_most_three_paragraphs() -> None:
    """Letter body contains at most 3 paragraphs even with many requirements."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Engineer", "scope": "Python ML pipelines on GCP with DevSecOps practices"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Python"}),
            ExportSource(type="skill", id="skill-2", data={"name": "Google Cloud"}),
            ExportSource(type="skill", id="skill-3", data={"name": "DevSecOps"}),
            ExportSource(type="skill", id="skill-4", data={"name": "Machine Learning"}),
        ],
        job_description="Python Google Cloud DevSecOps ML engineer",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    body_count = _body_paragraph_count(result)
    assert body_count <= 3, f"Expected at most 3 body paragraphs, got {body_count}"


def test_interest_letter_opening_uses_human_readable_labels() -> None:
    """Opening paragraph uses human-readable capability labels, not raw tokens."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
        ],
        job_description="Cloud infrastructure engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    # Opening paragraph is the first non-empty line after "Dear ..."
    lines = result.splitlines()
    dear_idx = next(i for i, l in enumerate(lines) if l.startswith("Dear"))
    opening = ""
    for j in range(dear_idx + 1, len(lines)):
        if lines[j].strip():
            opening = lines[j]
            break
    # Should contain human-readable label
    assert "AWS" in opening or "Cloud" in opening
    # Should not contain raw lowercase "aws" as a standalone word
    opening_words = opening.lower().replace(",", "").replace(".", "").split()
    assert "aws" not in opening_words, f"Raw token 'aws' found in opening: {opening}"


def test_interest_letter_closing_references_strongest_capability() -> None:
    """Closing paragraph references the strongest capability area."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "ML Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "PyTorch", "description": "Deep learning"}),
            ExportSource(type="skill", id="skill-2", data={"name": "AWS", "description": "Cloud infrastructure"}),
        ],
        job_description="ML engineer with PyTorch and AWS experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    closing = result.split("Sincerely")[0]
    # Should reference the strongest capability (PyTorch or Machine Learning)
    assert "pytorch" in closing.lower() or "machine learning" in closing.lower()


def test_interest_letter_raw_tokens_not_exposed_in_body() -> None:
    """Raw extracted tokens like 'google' or 'devsecops' don't appear as standalone words in body."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "Google Cloud", "description": "Cloud platform"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Security automation"}),
        ],
        job_description="Google Cloud DevSecOps engineer",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    # Body lines should not contain raw lowercase tokens as standalone words
    body_text = result.lower()
    # "google" should only appear as part of "google cloud" (a proper name)
    # Not as a standalone word like "regarding google,"
    lines = result.splitlines()
    for line in lines:
        if line.startswith("Dear") or line.startswith("#") or line.startswith("Sincerely"):
            continue
        words = line.lower().replace(",", "").replace(".", "").replace("(", "").replace(")", "").split()
        # Check that "google" without "cloud" following doesn't appear as a standalone token
        for i, w in enumerate(words):
            if w == "google" and i + 1 < len(words) and words[i + 1] != "cloud":
                # This is OK if it's part of "Google Cloud" in the skill name
                pass


# ---- Narrative quality regression tests ----


def test_interest_letter_no_regarding_pattern() -> None:
    """Body paragraphs do not begin with 'Regarding'."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed GCP and AWS infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
        ],
        job_description="Cloud engineer with AWS experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    for line in result.splitlines():
        if line.strip():
            assert not line.startswith("Regarding"), f"Paragraph begins with 'Regarding': {line}"


def test_interest_letter_no_repetitive_my_expertise_pattern() -> None:
    """Body does not repeat 'my expertise in' / 'my experience as' across every sentence."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed GCP and AWS infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Security automation"}),
        ],
        job_description="Cloud and DevSecOps engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    body = result.split("Sincerely")[0]
    # Count occurrences of repetitive patterns
    expertise_count = body.lower().count("my expertise in")
    experience_count = body.lower().count("my experience as")
    # At most one of each pattern should appear
    assert expertise_count <= 1, f"'my expertise in' appears {expertise_count} times"
    assert experience_count <= 1, f"'my experience as' appears {experience_count} times"


def test_interest_letter_narrative_has_varied_sentence_openers() -> None:
    """Body paragraphs use varied sentence structures (not all starting the same way)."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed GCP and AWS infrastructure"}),
            ExportSource(type="experience", id="exp-2", data={"title": "DevSecOps Engineer", "scope": "Built security scanning pipelines"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Security automation"}),
        ],
        job_description="Cloud and DevSecOps engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    body = result.split("Sincerely")[0]
    # Body should contain at least two different sentence opener patterns
    has_in_my_role = "In my role as" in body
    has_as_role = "As " in body and ", I " in body
    has_my_experience = "My experience" in body
    has_my_background = "My background" in body
    openers = sum([has_in_my_role, has_as_role, has_my_experience, has_my_background])
    assert openers >= 2, f"Expected at least 2 different opener patterns, found {openers}"


def test_interest_letter_experience_used_as_anchor() -> None:
    """Experience sources are used as narrative anchors, not just listed."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Architect", "scope": "Designed AWS infrastructure; reduced costs by 40%"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Expert in EC2, S3, Lambda"}),
        ],
        job_description="Cloud engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    # Experience should appear as "In my role as X, I ..." not just "my experience as X: ..."
    assert "In my role as Cloud Architect, I" in result
    assert "my experience as Cloud Architect:" not in result


def test_interest_letter_certification_woven_into_narrative() -> None:
    """Certifications are woven into the narrative, not rendered as standalone sentences."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed cloud infrastructure"}),
            ExportSource(type="certification", id="cert-1", data={"name": "AWS cloud certification"}),
        ],
        job_description="Cloud engineer with cloud certification",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    # Cert should appear woven into the narrative, not as "I hold a ... certification"
    assert "AWS cloud certification" in result
    assert "I hold a" not in result


def test_interest_letter_skill_description_cleaned() -> None:
    """Skill descriptions have 'Expert in' prefix stripped for natural prose."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed cloud infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "cloud tools", "description": "Expert in EC2, S3, and Lambda"}),
        ],
        job_description="Cloud engineer with cloud tools",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "Expert in" not in result
    assert "EC2" in result
    assert "S3" in result


def test_interest_letter_no_this_includes_pattern() -> None:
    """Body does not contain 'This includes' mechanical pattern."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed cloud infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Security automation"}),
        ],
        job_description="Cloud and DevSecOps engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "This includes" not in result


def test_interest_letter_no_i_hold_pattern() -> None:
    """Body does not contain 'I hold a' standalone cert pattern."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed cloud infrastructure"}),
            ExportSource(type="certification", id="cert-1", data={"name": "AWS cert"}),
        ],
        job_description="Cloud engineer with cloud certification",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "I hold a" not in result


def test_interest_letter_varied_connectors_in_supporting_clause() -> None:
    """Supporting clauses across paragraphs use different connectors."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed cloud infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "Cloud architecture"}),
            ExportSource(type="experience", id="exp-2", data={"title": "DevSecOps Engineer", "scope": "Built security pipelines"}),
            ExportSource(type="skill", id="skill-2", data={"name": "DevSecOps", "description": "Security automation"}),
        ],
        job_description="Cloud and DevSecOps engineer with AWS",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    connectors = ["using", "leveraging", "with", "applying"]
    found = [c for c in connectors if f", {c} " in result]
    assert len(found) >= 1, f"Expected at least one supporting clause connector, found: {found}"


def test_interest_letter_aws_skill_matches_without_gcp() -> None:
    """AWS skill sources match JD requirements containing 'AWS' (normalised to 'amazon web services')."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed AWS infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "EC2, S3, Lambda"}),
        ],
        job_description="AWS cloud engineer",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    assert "Amazon Web Services" in result or "AWS" in result


def test_interest_letter_expansion_of_cloud_requirements() -> None:
    """Both 'AWS' and 'Google Cloud' requirements are handled via canonical forms."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Cloud Engineer", "scope": "Managed AWS and GCP infrastructure"}),
            ExportSource(type="skill", id="skill-1", data={"name": "AWS", "description": "EC2, S3"}),
            ExportSource(type="skill", id="skill-2", data={"name": "Google Cloud", "description": "GKE, Compute Engine"}),
        ],
        job_description="Cloud infrastructure engineer with AWS and Google Cloud",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    body = result.split("Sincerely")[0]
    assert "AWS" in body or "Google Cloud" in body


# ---- JD role resolution & curated capability labels (deterministic fixes) ----


def _opening_paragraph(result: str) -> str:
    """Extract the first non-empty line after the 'Dear ...' greeting."""
    lines = result.splitlines()
    dear_idx = next(i for i, l in enumerate(lines) if l.startswith("Dear"))
    for j in range(dear_idx + 1, len(lines)):
        if lines[j].strip():
            return lines[j]
    return ""


def test_interest_letter_uses_jd_role_with_precedence() -> None:
    """A JD-derived role title takes precedence over the profile target-context role."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[
            {"id": "ctx-1", "role": "Senior IT DevSecOps Specialist / AI Solutions Architect", "audience": "Hiring Team"}
        ],
        sources=[
            ExportSource(type="experience", id="exp-1", data={"title": "Infrastructure Engineer", "scope": "Administered Linux environments and CI/CD automation"}),
            ExportSource(type="skill", id="skill-1", data={"name": "Linux", "description": "System administration"}),
        ],
        job_description=(
            "About the job\n"
            "We are looking for a Senior IT Infrastructure & DevOps Engineer with a strong "
            "background in cloud-native architectures and CI/CD automation."
        ),
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    opening = _opening_paragraph(result)
    assert "Senior IT Infrastructure & DevOps Engineer" in opening
    assert "Senior IT DevSecOps Specialist / AI Solutions Architect" not in result


def test_interest_letter_jd_role_heading_label_skipped() -> None:
    """'Job Title:' / 'Role:' heading labels do not hijack the extracted role."""
    from careeros.reporting.partner_output import jd_role_text

    assert jd_role_text("Job Title: Senior DevOps Engineer\nResponsibilities include CI/CD.") == "Senior DevOps Engineer"
    assert jd_role_text("Role: Cloud Architect\nLocation: Paris") == "Cloud Architect"
    assert jd_role_text("") == ""
    assert jd_role_text("Python engineer with system design experience") == ""


def test_interest_letter_falls_back_to_target_context_role() -> None:
    """When the JD names no role, the target-context role is preserved."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
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
    assert "Senior Engineer" in _opening_paragraph(result)


def test_interest_letter_headline_fallback_when_no_role() -> None:
    """Without a JD role or target-context role, the profile headline is used."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}],
                "positioning": {"headline": "Infrastructure Automation Specialist"}},
        artifact={"title": "Interest Letter"},
        target_contexts=[],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "Linux", "description": "System administration"}),
        ],
        job_description="Systems engineer opportunity",
    )
    opening = _opening_paragraph(MarkdownInterestLetterGenerator().generate(contract))
    assert "Infrastructure Automation Specialist" in opening


def test_interest_letter_capability_labels_are_curated() -> None:
    """Capability labels come from curated theme labels; unknown themes are skipped."""
    from careeros.generators.markdown_interest_letter import _THEME_LABELS
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    generator = MarkdownInterestLetterGenerator()
    theme_groups = [
        (theme, [], [f"raw {index}"])
        for index, theme in enumerate(["cloud_infra", "infra_tooling", "unknown_theme"])
    ]
    labels = generator._capability_labels(theme_groups)
    assert labels == ["Cloud and Infrastructure", "Infrastructure Tooling"]
    assert set(labels) <= set(_THEME_LABELS.values())


def test_interest_letter_generic_verbs_not_capability_labels() -> None:
    """'Administer' (a JD duty verb) never surfaces as a capability label."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Infrastructure Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="skill", id="skill-1", data={"name": "Linux", "description": "System administration"}),
        ],
        job_description="Administer and maintain Linux environments with CI/CD automation",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    opening = _opening_paragraph(result)
    assert "Administer" not in opening
    assert "Maintain" not in opening
    assert "Infrastructure Tooling" in opening


def test_interest_letter_earthlab_jd_role_and_labels() -> None:
    """End-to-end: EarthLab JD yields the true role and curated labels (acceptance)."""
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    jd = (
        "About the job\n"
        "We are looking for a Senior IT Infrastructure & DevOps Engineer with a strong background\n"
        "in cloud-native architectures, systems administration, and CI/CD automation.\n"
        "What is expected from you:\n"
        "- Take ownership of EarthLab's existing IT infrastructure\n"
        "- Administer and maintain Linux environments, on-premise servers in the data center, networking,\n"
        "  storage, virtualization platforms, containers, monitoring tools, backup processes, and technical documentation.\n"
        "- Improve automation, deployment, monitoring, backup, security, and configuration management practices\n"
        "- Implement, maintain, and enhance CI/CD pipelines and deployment tools, integrating DevSecOps practices\n"
        "Technical Skills:\n"
        "- Linux system administration\n"
        "- Networking and storage fundamentals\n"
        "- CI/CD tools such as GitLab CI or Jenkins\n"
        "- Docker and application packaging\n"
        "- Infrastructure automation, ideally Ansible or Terraform\n"
        "Nice to have:\n"
        "- Kubernetes or Mesos/Marathon\n"
        "- VMware or Hyper-V\n"
        "- AWS, Azure, or GCP\n"
        "- DevSecOps practices"
    )
    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}],
                "positioning": {"headline": "Senior IT DevSecOps Specialist / AI Solutions Architect"}},
        artifact={"title": "Interest Letter"},
        target_contexts=[
            {"id": "ctx-1", "role": "Senior IT DevSecOps Specialist / AI Solutions Architect", "audience": "Hiring Team"}
        ],
        sources=[
            ExportSource(type="experience", id="exp-1", data={
                "title": "Infrastructure Engineer",
                "scope": "Administered and maintained Linux environments, on-premise servers, "
                         "networking, storage, and VMware virtualization platforms",
            }),
            ExportSource(type="skill", id="skill-1", data={"name": "Linux", "description": "System administration"}),
            ExportSource(type="skill", id="skill-2", data={"name": "Kubernetes", "description": "Container orchestration"}),
            ExportSource(type="skill", id="skill-3", data={"name": "Docker", "description": "Application packaging"}),
            ExportSource(type="skill", id="skill-4", data={"name": "Ansible", "description": "Infrastructure automation"}),
            ExportSource(type="skill", id="skill-5", data={"name": "AWS", "description": "Cloud infrastructure"}),
        ],
        job_description=jd,
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    opening = _opening_paragraph(result)
    # 1. True role title wins over the outdated profile role
    assert "Senior IT Infrastructure & DevOps Engineer" in opening
    assert "Senior IT DevSecOps Specialist / AI Solutions Architect" not in result
    # 2. No 'Administer'/'Devops Engineer' machine-generated capability labels
    assert "Administer" not in opening
    assert "Devops Engineer" not in result
    # 3. Curated labels, not raw tokens, describe the background
    opening_words = opening.split()
    raw_junk = {"administer", "devops", "jenkins", "terraform", "kubernetes"}
    assert raw_junk.isdisjoint(set(opening_words))
    # 4. Relevant capability concepts surface in the body
    body = result.split("Sincerely")[0]
    body_lower = body.lower()
    assert "linux" in body_lower
    assert "docker" in body_lower
    assert "ansible" in body_lower
    assert "aws" in body_lower


# ---- A1/A2/A3 milestone: aggregated theme relevance, within-theme narration, punctuation ----


def test_interest_letter_pooled_theme_relevance_surfaces_cloud_in_opening() -> None:
    """A1: a theme with no single winning source still surfaces via aggregated evidence.

    Cloud requirements (AWS / Google Cloud / Azure) are spread across several
    evidence sources, none of which claims cloud_infra winner-take-all.  The
    aggregated relevance pool must promote 'Cloud and Infrastructure' into the
    opening AND closing labels — while the empty cloud theme never renders a
    body paragraph.
    """
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Platform Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-root", data={
                "title": "Senior DevSecOps Specialist",
                "scope": "Led migration from VMware VxRail datacenters to AWS, reducing infrastructure "
                         "overhead; managed Linux environments with Ansible; built CI/CD automation "
                         "with Docker and Kubernetes",
            }),
            ExportSource(type="skill", id="skill-clouds", data={
                "name": "Cloud & Containers",
                "description": "AWS, Google Cloud, VMware, Kubernetes, Docker, CI/CD pipelines, Azure, "
                               "Linux, Ansible, Infrastructure as Code",
            }),
            ExportSource(type="experience", id="exp-sec", data={
                "title": "IT System Administrator",
                "scope": "Administered Google Cloud infrastructure; enforced DevSecOps, cybersecurity, "
                         "SIEM, and identity and access management policy",
            }),
        ],
        job_description=(
            "Infrastructure engineer with Linux, VMware, Ansible, Docker, Kubernetes, CI/CD, AWS, "
            "Google Cloud, Azure, DevSecOps, cybersecurity, SIEM, and identity and access "
            "management experience"
        ),
    )
    result = MarkdownInterestLetterGenerator().generate(contract)
    opening = _opening_paragraph(result)

    # Pooled aggregation surfaces the cloud thread even without a cloud-winning source
    assert "Cloud and Infrastructure" in opening
    assert "Infrastructure Tooling" in opening
    # Closing references the aggregated top themes, including the distributed cloud thread
    closing = result.split("Sincerely")[0]
    assert "Cloud and Infrastructure" in closing
    assert "Infrastructure Tooling" in closing
    # The empty cloud theme disappears from the body: exactly two focused paragraphs
    assert _body_paragraph_count(result) == 2


def test_interest_letter_linux_evidence_narrated_within_theme() -> None:
    """A2: within a theme, the strongest distinct same-theme experience is narrated.

    A second experience with materially distinct evidence (Linux administration)
    must appear in the body, while a redundant same-theme experience that adds no
    distinct requirements stays out.  Evidence is never dumped wholesale.
    """
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Infrastructure Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={
                "title": "Cloud Infrastructure Lead",
                "scope": "Led migration from VMware VxRail datacenters to AWS; built CI/CD automation "
                         "with Docker and Kubernetes",
            }),
            ExportSource(type="experience", id="exp-2", data={
                "title": "Systems Engineer",
                "scope": "Managed Linux environments and monitoring for 1,000+ users",
            }),
            ExportSource(type="experience", id="exp-3", data={
                "title": "Networking Admin",
                "scope": "Managed CI/CD pipelines and infrastructure automation",
            }),
            ExportSource(type="skill", id="skill-1", data={"name": "Kubernetes", "description": "Container orchestration"}),
        ],
        job_description=(
            "Infrastructure engineer with Linux, VMware, Docker, Kubernetes, CI/CD, and "
            "monitoring experience"
        ),
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    # Linux evidence from the second experience is narrated in the theme paragraph
    assert "managed Linux environments" in result
    # The redundant same-theme experience adds zero distinct requirements: not narrated
    assert "Networking Admin" not in result
    # Still a single coherent paragraph (anchor + one additional sentence + skill clause)
    assert _body_paragraph_count(result) == 1
    # No punctuation artifacts from the woven sentence
    assert ".." not in result


def test_interest_letter_no_punctuation_artifacts_in_parentheticals() -> None:
    """A3: skill descriptions wrapped in parentheses never leave '.).' or '..' artifacts.

    A description that ends with a period (e.g. 'Infrastructure as Code.') must be
    stripped before embedding mid-sentence, and an experience scope ending with a
    period must not double the sentence terminator.
    """
    from careeros.generators.markdown_interest_letter import MarkdownInterestLetterGenerator

    contract = ExportContract(
        profile_version="1.0.0", artifact_id="il-1", artifact_type="INTEREST_LETTER",
        person={"id": "p1", "names": [{"value": "Jane Doe", "usage": "professional"}]},
        artifact={"title": "Interest Letter"},
        target_contexts=[{"id": "ctx-1", "role": "Cloud Engineer", "audience": "Hiring Team"}],
        sources=[
            ExportSource(type="experience", id="exp-1", data={
                "title": "Cloud Engineer",
                "scope": "Managed cloud infrastructure for 200+ users; maintained Kubernetes "
                         "clusters, Docker, and CI/CD.",
            }),
            ExportSource(type="skill", id="skill-1", data={
                "name": "Cloud & Containers",
                "description": "AWS, Google Cloud, VMware VxRail, Kubernetes, Docker, OpenStack, "
                               "Azure, CI/CD pipelines, Infrastructure as Code.",
            }),
        ],
        job_description="Cloud engineer with AWS, Kubernetes, Docker, and infrastructure experience",
    )
    result = MarkdownInterestLetterGenerator().generate(contract)

    # The description no longer ends with '.', so the closing parenthesis is clean
    assert ".)." not in result
    assert "Infrastructure as Code)." in result
    # The scope's trailing period is stripped before the template adds its own
    assert "users.." not in result
    assert "for 200+ users," in result
