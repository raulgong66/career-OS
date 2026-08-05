from pathlib import Path

import pytest

from careeros.exceptions import ValidationError
from careeros.export_contract import ExportContractBuilder
from careeros.generators import MarkdownCVGenerator
from careeros.schema_loader import SchemaLoader


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def profile() -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {
                "headline": "AI product builder",
                "valueProposition": "Builds reliable AI workflows",
                "targetDirection": "AI platform roles",
                "themes": ["AI", "Product"],
            },
        },
        "professionalSummaries": [
            {
                "id": "summary-1",
                "text": "AI product builder focused on reliable workflow systems.",
            }
        ],
        "experiences": [
            {
                "id": "experience-1",
                "title": "Product Engineer",
                "dateRange": {"start": "2024", "end": "2026"},
                "scope": "Built AI-native career workflows.",
            }
        ],
        "projects": [
            {
                "id": "project-1",
                "name": "CareerOS",
                "description": "Schema-driven career operating system.",
            }
        ],
        "skills": [
            {
                "id": "skill-1",
                "name": "AI workflow design",
                "category": "AI",
            }
        ],
        "achievements": [
            {
                "id": "achievement-1",
                "statement": "Reduced manual tailoring effort through structured reuse.",
            }
        ],
        "education": [
            {
                "id": "education-1",
                "program": "MSc",
                "fieldOfStudy": "Computer Science",
            }
        ],
        "certifications": [
            {
                "id": "certification-1",
                "name": "AI Product Certification",
                "credentialId": "CERT-1",
            }
        ],
        "targetContexts": [
            {
                "id": "context-1",
                "label": "AI platform role",
                "role": "AI Product Engineer",
                "market": "AI platforms",
                "language": "en",
            }
        ],
        "artifacts": [
            {
                "id": "artifact-1",
                "title": "AI Platform CV",
                "artifactType": "CV",
                "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                "sourceRefs": [
                    {"id": "summary-1", "type": "professional_summary"},
                    {"id": "experience-1", "type": "experience"},
                    {"id": "project-1", "type": "project"},
                    {"id": "skill-1", "type": "skill"},
                    {"id": "achievement-1", "type": "achievement"},
                    {"id": "education-1", "type": "education"},
                    {"id": "certification-1", "type": "certification"},
                ],
                "derivedFromProfileVersion": "1.0.0",
            }
        ],
    }


def test_markdown_cv_generator_uses_only_export_contract(repo_root: Path, profile: dict) -> None:
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert markdown.startswith("# Jane Doe\n")
    assert "AI product builder" in markdown
    assert "## Professional Summary" in markdown
    assert "AI product builder focused on reliable workflow systems." in markdown
    assert "## Core Competencies" in markdown
    assert "AI workflow design" in markdown
    assert "## Professional Experience" in markdown
    assert "Product Engineer" in markdown
    assert "Built AI-native career workflows." in markdown
    assert "## Projects" in markdown
    assert "**CareerOS**: Schema-driven career operating system." in markdown
    assert "## Education" in markdown
    assert "MSc in Computer Science" in markdown
    assert "## Certifications" in markdown
    assert "AI Product Certification" in markdown

    # No internal implementation metadata leaks into the document
    for leak in ("Artifact:", "Derived from profile version", "profileVersion", "artifact_id", "artifactId"):
        assert leak not in markdown

    # Individual entries render as plain text, never as headings
    assert not any(line.startswith("###") for line in markdown.splitlines())


def test_markdown_cv_generator_preserves_contract_source_order_within_sections(repo_root: Path, profile: dict) -> None:
    profile["skills"].append({"id": "skill-2", "name": "Schema design"})
    profile["artifacts"][0]["sourceRefs"].extend(
        [
            {"id": "skill-2", "type": "skill"},
        ]
    )
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert markdown.index("AI workflow design") < markdown.index("Schema design")


def test_markdown_cv_generator_rejects_non_cv_contract(repo_root: Path, profile: dict) -> None:
    profile["artifacts"][0]["artifactType"] = "PORTFOLIO"
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    with pytest.raises(ValidationError, match="Unsupported artifact type"):
        MarkdownCVGenerator().generate(contract)


def test_markdown_cv_renders_linked_achievement_under_experience(repo_root: Path, profile: dict) -> None:
    """Achievement sources linked to an experience render as bullets under it."""
    profile["experiences"][0]["achievementRefs"] = [{"id": "achievement-2", "type": "achievement"}]
    profile["achievements"].append(
        {
            "id": "achievement-2",
            "statement": "Reduced deployment time by 60% through CI/CD automation.",
            "contextRefs": [{"id": "experience-1", "type": "experience"}],
        }
    )
    profile["artifacts"][0]["sourceRefs"].append({"id": "achievement-2", "type": "achievement"})
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert "Reduced deployment time by 60% through CI/CD automation." in markdown
    # Rendered under the experience, not as an internal id or source ref
    assert "achievement-2" not in markdown
    assert "sourceRefs" not in markdown
    assert "• Reduced deployment time by 60% through CI/CD automation." in markdown


def test_markdown_cv_links_achievement_via_context_refs(repo_root: Path, profile: dict) -> None:
    """An achievement source with contextRefs to an experience is placed under it."""
    profile["achievements"].append(
        {
            "id": "achievement-2",
            "statement": "Cut infrastructure cost by 25% while migrating 40 microservices.",
            "contextRefs": [{"id": "experience-1", "type": "experience"}],
        }
    )
    profile["artifacts"][0]["sourceRefs"].append({"id": "achievement-2", "type": "achievement"})
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert "Cut infrastructure cost by 25% while migrating 40 microservices." in markdown
    assert "achievement-2" not in markdown


def test_markdown_cv_renders_location_display_objects_as_text(repo_root: Path, profile: dict) -> None:
    """Location display objects render via their human-readable field, never as Python reprs."""
    profile["person"]["location"] = {"label": "Netherlands"}
    profile["experiences"][0]["location"] = {"label": "Amsterdam"}
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert "Netherlands" in markdown
    assert "Amsterdam" in markdown
    assert "'label'" not in markdown
    assert "{" not in markdown


def test_markdown_cv_renders_location_city_country_parts(repo_root: Path, profile: dict) -> None:
    """Locations without a label compose a label from city/region/country parts."""
    profile["person"]["location"] = {"city": "Stockholm", "country": "Sweden"}
    profile["experiences"][0]["location"] = {"city": "Utrecht", "country": "Netherlands"}
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert "Stockholm, Sweden" in markdown
    assert "Utrecht, Netherlands" in markdown
    assert "{" not in markdown
