from pathlib import Path

import yaml
from typer.testing import CliRunner

from careeros_cli.main import app


runner = CliRunner()


def test_help_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip()


def test_validate_command_accepts_valid_profile(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {
                    "id": "person-1",
                    "names": [{"value": "Jane Doe", "usage": "professional"}],
                    "contact": {"email": "jane@example.com"},
                    "location": {"city": "Stockholm"},
                    "positioning": {
                        "headline": "Product engineer",
                        "valueProposition": "Builds reliable systems",
                        "targetDirection": "Growth",
                        "themes": ["Engineering"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", "profile", str(profile_file)])

    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_create_command_writes_entity_file(tmp_path: Path) -> None:
    output_file = tmp_path / "company.json"

    result = runner.invoke(app, ["create", "company", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()


def test_list_command_lists_entities(tmp_path: Path) -> None:
    first = tmp_path / "alpha.json"
    second = tmp_path / "beta.json"
    first.write_text('{"id": "alpha", "name": "Alpha", "metadata": {"id": "alpha", "version": "1.0.0", "status": "ACTIVE"}}', encoding="utf-8")
    second.write_text('{"id": "beta", "name": "Beta", "metadata": {"id": "beta", "version": "1.0.0", "status": "ACTIVE"}}', encoding="utf-8")

    result = runner.invoke(app, ["list", "company", str(tmp_path)])

    assert result.exit_code == 0
    assert "alpha" in result.stdout
    assert "beta" in result.stdout


def test_generate_markdown_cv_command_writes_output_file(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    output_file = tmp_path / "outputs" / "cv.md"
    profile_file.write_text(
        yaml.safe_dump(
            {
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
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "targetContexts": [{"id": "context-1", "role": "AI Product Engineer"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "title": "AI Platform CV",
                        "artifactType": "CV",
                        "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["generate-markdown-cv", str(profile_file), "artifact-1", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()
    assert "# Jane Doe" in output_file.read_text(encoding="utf-8")
    assert "- AI workflow design" in output_file.read_text(encoding="utf-8")


def test_generate_markdown_cv_command_reports_missing_artifact(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    output_file = tmp_path / "cv.md"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1"},
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["generate-markdown-cv", str(profile_file), "missing", str(output_file)])

    assert result.exit_code == 1
    assert "Artifact not found" in result.stdout
    assert not output_file.exists()


def test_generate_markdown_cv_command_filters_context_specific_sources(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    output_file = tmp_path / "cv.md"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [
                    {
                        "id": "skill-match",
                        "name": "Matching skill",
                    },
                    {
                        "id": "skill-other",
                        "name": "Other skill",
                    },
                ],
                "targetContexts": [{"id": "context-1", "role": "AI Product Engineer"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                        "sourceRefs": [
                            {
                                "id": "skill-match",
                                "type": "skill",
                                "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                            },
                            {
                                "id": "skill-other",
                                "type": "skill",
                                "targetContextRefs": [{"id": "context-2", "type": "targetContext"}],
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["generate-markdown-cv", str(profile_file), "artifact-1", str(output_file)])

    assert result.exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert "Matching skill" in markdown
    assert "Other skill" not in markdown


def test_generate_artifact_command_writes_markdown_output_file(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    output_file = tmp_path / "cv.md"
    profile_file.write_text(
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

    result = runner.invoke(app, ["generate-artifact", str(profile_file), "artifact-1", "markdown", str(output_file)])

    assert result.exit_code == 0
    assert "# Jane Doe" in output_file.read_text(encoding="utf-8")
    assert "- AI workflow design" in output_file.read_text(encoding="utf-8")


def test_generate_artifact_command_writes_docx_output_file(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    output_file = tmp_path / "cv.docx"
    profile_file.write_text(
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

    result = runner.invoke(app, ["generate-artifact", str(profile_file), "artifact-1", "docx", str(output_file)])

    assert result.exit_code == 0
    assert output_file.read_bytes().startswith(b"PK")
