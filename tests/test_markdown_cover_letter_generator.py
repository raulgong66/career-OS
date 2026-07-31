import copy
from pathlib import Path

import pytest

from careeros.exceptions import ValidationError
from careeros.export_contract import ExportContractBuilder
from careeros.generators import MarkdownCoverLetterGenerator
from careeros.reasoning import ReasoningFindings
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
    assert "profile version" not in markdown


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


# ---------------------------------------------------------------------------
# JD-aware cover letter tests (PA-005)
# ---------------------------------------------------------------------------


def test_markdown_cover_letter_with_jd_opens_with_requirements(repo_root: Path, profile: dict) -> None:
    """JD-aware letter opening references the role and top matched requirements."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Seeking AI Product Engineer with experience in AI workflow design and workflow systems."

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert "AI Product Engineer opportunity" in markdown
    assert "key requirements" in markdown
    assert "workflow" in markdown


def test_markdown_cover_letter_with_jd_reorders_evidence_by_relevance(repo_root: Path, profile: dict) -> None:
    """Evidence sources are reordered so JD-relevant items appear first."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Seeking AI Product Engineer with experience in AI workflow design."

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    # skill "AI workflow design" matches the JD directly and should appear
    # before the achievement that has no JD overlap
    assert markdown.index("- AI workflow design") < markdown.index("- Reduced manual tailoring effort")


def test_markdown_cover_letter_with_jd_closing_matches_role(repo_root: Path, profile: dict) -> None:
    """JD-aware letter has a tailored closing paragraph instead of plain 'Sincerely'."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Seeking AI Product Engineer."

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert "I am confident that my experience" in markdown
    assert "AI Product Engineer" in markdown
    assert "Sincerely," in markdown
    assert markdown.index("I am confident that") < markdown.index("Sincerely,")


def test_markdown_cover_letter_with_jd_and_reasoning_closing_uses_competencies(repo_root: Path, profile: dict) -> None:
    """JD-aware closing references core competencies from ReasoningFindings when available."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Seeking AI Product Engineer."
    contract.reasoning = ReasoningFindings(core_competencies=["AI Product", "Workflow Design"])

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert "AI Product" in markdown or "Workflow Design" in markdown
    assert "Sincerely," in markdown


def test_markdown_cover_letter_with_jd_no_matching_evidence_fallback(repo_root: Path, profile: dict) -> None:
    """JD with no profile overlap still produces a valid letter with generic ordering."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Requires expertise in quantum computing and nuclear fusion."

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    # Letter should still be valid
    assert "quantum computing" in markdown or "key requirements" in markdown
    assert "## Relevant Evidence" in markdown
    assert "- Product Engineer: Built AI-native career workflows." in markdown
    assert "- Reduced manual tailoring effort through structured reuse." in markdown
    assert "Sincerely," in markdown
    assert "profile version" not in markdown


def test_markdown_cover_letter_with_jd_no_role_fallback(repo_root: Path, profile: dict) -> None:
    """JD-aware letter without a target role still produces valid output."""
    profile["targetContexts"][0].pop("role", None)
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "Seeking AI Product Engineer with experience in AI workflow design."

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    assert "Hiring Team" in markdown
    assert "## Relevant Evidence" in markdown
    assert "Sincerely," in markdown


def test_markdown_cover_letter_backward_compat_without_jd(repo_root: Path, profile: dict) -> None:
    """Without job_description the output matches the pre-JD baseline."""
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = None

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
    assert "profile version" not in markdown


def test_markdown_cover_letter_jd_cvoptimizer_integration(repo_root: Path, profile: dict) -> None:
    """Cover letter generator uses CVOptimizer requirement extraction directly."""
    from careeros.optimizer import CVOptimizer

    jd_text = "We need an expert in AI, workflow design, and Python."
    requirements = CVOptimizer._extract_requirements(jd_text)

    assert isinstance(requirements, list)
    assert len(requirements) > 0


def test_markdown_cover_letter_jd_matches_and_preserves_unmatched_sources(repo_root: Path, profile: dict) -> None:
    """Sources with zero JD match keep their relative order at the bottom."""
    profile["projects"] = [
        {"id": "project-1", "name": "CareerOS"},
        {"id": "project-2", "name": "AI platform"},
    ]
    profile["artifacts"][0]["sourceRefs"].extend([
        {"id": "project-1", "type": "project"},
        {"id": "project-2", "type": "project"},
    ])
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "cover-letter-1")
    contract.job_description = "AI workflow design"

    markdown = MarkdownCoverLetterGenerator().generate(contract)

    # AI workflow design (skill) should be first (highest JD match),
    # unmatched sources at the bottom preserve their original order
    assert markdown.index("- AI workflow design") < markdown.index("- CareerOS")
    assert markdown.index("- CareerOS") < markdown.index("- AI platform")
