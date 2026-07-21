from pathlib import Path

import pytest

from careeros.exceptions import ValidationError
from careeros.export_contract import ExportContractBuilder
from careeros.generators import MarkdownCoverLetterGenerator
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
                "scope": "Built AI-native career workflows.",
            }
        ],
        "skills": [
            {
                "id": "skill-1",
                "name": "AI workflow design",
                "description": "Designs deterministic AI-assisted workflows.",
            }
        ],
        "achievements": [
            {
                "id": "achievement-1",
                "statement": "Reduced manual tailoring effort through structured reuse.",
            }
        ],
        "targetContexts": [
            {
                "id": "context-1",
                "audience": "Hiring Team",
                "role": "AI Product Engineer",
            }
        ],
        "artifacts": [
            {
                "id": "cover-letter-1",
                "title": "AI Product Engineer Cover Letter",
                "artifactType": "COVER_LETTER",
                "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                "sourceRefs": [
                    {"id": "summary-1", "type": "professional_summary"},
                    {"id": "experience-1", "type": "experience"},
                    {"id": "skill-1", "type": "skill"},
                    {"id": "achievement-1", "type": "achievement"},
                ],
            }
        ],
    }


def test_markdown_cover_letter_generator_uses_only_export_contract(repo_root: Path, profile: dict) -> None:
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert markdown.startswith("# AI Product Engineer Cover Letter\n")
    assert "Dear Hiring Team," in markdown
    assert "AI Product Engineer opportunity" in markdown
    assert "AI product builder focused on reliable workflow systems." in markdown
    assert "## Relevant Evidence" in markdown
    assert "- Product Engineer: Built AI-native career workflows." in markdown
    assert "- AI workflow design: Designs deterministic AI-assisted workflows." in markdown
    assert "- Reduced manual tailoring effort through structured reuse." in markdown
    assert "Sincerely,\n\nJane Doe" in markdown
    assert "_Derived from profile version: 1.0.0_" in markdown


def test_markdown_cover_letter_generator_preserves_source_order(repo_root: Path, profile: dict) -> None:
    profile["projects"] = [{"id": "project-1", "name": "CareerOS"}]
    profile["artifacts"][0]["sourceRefs"].append({"id": "project-1", "type": "project"})
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert markdown.index("- Product Engineer") < markdown.index("- AI workflow design")
    assert markdown.index("- AI workflow design") < markdown.index("- Reduced manual tailoring effort")
    assert markdown.index("- Reduced manual tailoring effort") < markdown.index("- CareerOS")


def test_markdown_cover_letter_generator_rejects_non_cover_letter(repo_root: Path, profile: dict) -> None:
    profile["artifacts"][0]["artifactType"] = "CV"
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")

    with pytest.raises(ValidationError, match="Unsupported artifact type"):
        MarkdownCoverLetterGenerator().generate(contract)
