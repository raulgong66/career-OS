from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from careeros.exceptions import ValidationError
from careeros.export_contract import ExportContractBuilder
from careeros.generators import DocxCVGenerator
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
                "themes": ["AI"],
            },
        },
        "professionalSummaries": [
            {
                "id": "summary-1",
                "text": "AI product builder focused on reliable workflow systems.",
            }
        ],
        "skills": [{"id": "skill-1", "name": "AI workflow design"}],
        "artifacts": [
            {
                "id": "artifact-1",
                "title": "AI Platform CV",
                "artifactType": "CV",
                "sourceRefs": [
                    {"id": "summary-1", "type": "professional_summary"},
                    {"id": "skill-1", "type": "skill"},
                ],
            }
        ],
    }


def test_docx_cv_generator_returns_docx_bytes(repo_root: Path, profile: dict) -> None:
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    output = DocxCVGenerator().generate(contract)

    assert isinstance(output, bytes)
    assert output.startswith(b"PK")


def test_docx_cv_generator_renders_expected_content(repo_root: Path, profile: dict) -> None:
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    output = DocxCVGenerator().generate(contract)
    document = Document(BytesIO(output))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Jane Doe" in text
    assert "AI product builder" in text
    assert "AI Platform CV" in text
    assert "Professional Summary" in text
    assert "AI product builder focused on reliable workflow systems." in text
    assert "AI workflow design" in text
    assert "Derived from profile version: 1.0.0" in text


def test_docx_cv_generator_rejects_non_cv_contract(repo_root: Path, profile: dict) -> None:
    profile["artifacts"][0]["artifactType"] = "PORTFOLIO"
    contract = ExportContractBuilder(SchemaLoader(repo_root / "schemas")).build(profile, "artifact-1")

    with pytest.raises(ValidationError, match="Unsupported artifact type"):
        DocxCVGenerator().generate(contract)
