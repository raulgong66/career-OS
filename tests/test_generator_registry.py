from pathlib import Path

import pytest
import yaml

from careeros.exceptions import ValidationError
from careeros.export_contract import ExportContract
from careeros.generators import (
    DocxCVGenerator,
    GeneratorRegistry,
    MarkdownCoverLetterGenerator,
    MarkdownCVGenerator,
    default_generator_registry,
)
from careeros.pipelines import generate_artifact, generate_markdown_cv
from careeros.schema_loader import SchemaLoader


class FakeGenerator:
    def generate(self, contract: ExportContract) -> str:
        return f"{contract.artifact_type}:{contract.artifact_id}:{len(contract.sources)}"


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def profile_file(tmp_path: Path) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_generator_registry_resolves_by_artifact_type_and_format() -> None:
    registry = GeneratorRegistry()
    generator = FakeGenerator()

    registry.register("CV", "markdown", generator)

    assert registry.resolve("cv", "MARKDOWN") is generator


def test_generator_registry_reports_missing_generator() -> None:
    registry = GeneratorRegistry()

    with pytest.raises(ValidationError, match="No generator registered"):
        registry.resolve("CV", "html")


def test_default_generator_registry_preserves_markdown_cv_behavior() -> None:
    generator = default_generator_registry().resolve("CV", "markdown")

    assert isinstance(generator, MarkdownCVGenerator)


def test_default_generator_registry_registers_docx_cv_generator() -> None:
    generator = default_generator_registry().resolve("CV", "docx")

    assert isinstance(generator, DocxCVGenerator)


def test_default_generator_registry_registers_markdown_cover_letter_generator() -> None:
    generator = default_generator_registry().resolve("COVER_LETTER", "markdown")

    assert isinstance(generator, MarkdownCoverLetterGenerator)


def test_pipeline_resolves_generator_via_registry(repo_root: Path, profile_file: Path) -> None:
    registry = GeneratorRegistry()
    registry.register("CV", "text", FakeGenerator())

    output = generate_artifact(profile_file, "artifact-1", "text", SchemaLoader(repo_root / "schemas"), registry)

    assert output == "CV:artifact-1:1"


def test_markdown_cv_pipeline_uses_default_registry(repo_root: Path, profile_file: Path) -> None:
    output = generate_markdown_cv(profile_file, "artifact-1", SchemaLoader(repo_root / "schemas"))

    assert "# Jane Doe" in output
    assert "- AI workflow design" in output


def test_pipeline_generates_markdown_cover_letter_with_default_registry(repo_root: Path, tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "targetContexts": [{"id": "context-1", "audience": "Hiring Team", "role": "AI Product Engineer"}],
                "artifacts": [
                    {
                        "id": "cover-letter-1",
                        "title": "AI Product Engineer Cover Letter",
                        "artifactType": "COVER_LETTER",
                        "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    output = generate_artifact(profile_file, "cover-letter-1", "markdown", SchemaLoader(repo_root / "schemas"))

    assert "# AI Product Engineer Cover Letter" in output
    assert "Dear Hiring Team," in output
    assert "- AI workflow design" in output
