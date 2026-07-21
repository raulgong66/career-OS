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
    assert "**Artifact:** AI Platform CV" in markdown
    assert "## Target Context\nAI Product Engineer, AI platforms, en" in markdown
    assert "## Professional Summary" in markdown
    assert "- AI product builder focused on reliable workflow systems." in markdown
    assert "- **Product Engineer** (2024 - 2026): Built AI-native career workflows." in markdown
    assert "- **CareerOS**: Schema-driven career operating system." in markdown
    assert "- AI workflow design (AI)" in markdown
    assert "- Reduced manual tailoring effort through structured reuse." in markdown
    assert "- MSc in Computer Science" in markdown
    assert "- AI Product Certification (Credential ID: CERT-1)" in markdown
    assert "_Derived from profile version: 1.0.0_" in markdown


def test_markdown_cv_generator_preserves_contract_source_order_within_sections(repo_root: Path, profile: dict) -> None:
    profile["skills"].append({"id": "skill-2", "name": "Schema design"})
    profile["artifacts"][0]["sourceRefs"].extend(
        [
            {"id": "skill-2", "type": "skill"},
        ]
    )
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    markdown = MarkdownCVGenerator().generate(contract)

    assert markdown.index("- AI workflow design (AI)") < markdown.index("- Schema design")


def test_markdown_cv_generator_rejects_non_cv_contract(repo_root: Path, profile: dict) -> None:
    profile["artifacts"][0]["artifactType"] = "PORTFOLIO"
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    with pytest.raises(ValidationError, match="Unsupported artifact type"):
        MarkdownCVGenerator().generate(contract)
