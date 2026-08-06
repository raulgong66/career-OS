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
    assert "AI workflow design" in output_file.read_text(encoding="utf-8")


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

    # The Core Competencies section must only include context-matching skills
    skills_section_start = markdown.index("## Core Competencies")
    after_skills = markdown[skills_section_start:]
    assert "Matching skill" in after_skills
    assert "Other skill" not in after_skills


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
    assert "AI workflow design" in output_file.read_text(encoding="utf-8")


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


def test_analyze_profile_command_prints_report_json(tmp_path: Path) -> None:
    """careeros analyze-profile <file> prints the report as JSON to stdout."""
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump({
            "profileVersion": "1.0.0",
            "person": {"id": "test-person"},
            "experiences": [],
            "skills": [],
            "education": [],
            "organizations": [],
            "professionalSummaries": [],
            "projects": [],
            "achievements": [],
            "evidence": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
        }),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-profile", str(profile_file)])

    assert result.exit_code == 0
    import json
    report = json.loads(result.stdout)
    assert report["engine_version"] == "1.0.0"
    assert report["profile_id"] == "test-person"
    assert "findings" in report
    assert "findings_by_type" in report
    assert "summary" in report
    assert "execution_stats" in report


def test_analyze_profile_command_writes_output_file(tmp_path: Path) -> None:
    """careeros analyze-profile <file> --output writes the report to a file."""
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump({
            "profileVersion": "1.0.0",
            "person": {"id": "test-person"},
            "experiences": [],
            "skills": [],
            "education": [],
            "organizations": [],
            "professionalSummaries": [],
            "projects": [],
            "achievements": [],
            "evidence": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
        }),
        encoding="utf-8",
    )
    output_file = tmp_path / "report.json"

    result = runner.invoke(app, ["analyze-profile", str(profile_file), "--output", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()
    import json
    report = json.loads(output_file.read_text(encoding="utf-8"))
    assert report["profile_id"] == "test-person"


def test_analyze_profile_command_summary_flag(tmp_path: Path) -> None:
    """careeros analyze-profile <file> --summary prints a short summary."""
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump({
            "profileVersion": "1.0.0",
            "person": {"id": "test-person"},
            "experiences": [],
            "skills": [],
            "education": [],
            "organizations": [],
            "professionalSummaries": [],
            "projects": [],
            "achievements": [],
            "evidence": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
        }),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-profile", str(profile_file), "--summary"])

    assert result.exit_code == 0
    assert "Total Findings:" in result.stdout
    assert "Rules Executed:" in result.stdout
    assert "Execution Time:" in result.stdout


def test_analyze_profile_command_pretty_flag(tmp_path: Path) -> None:
    """careeros analyze-profile <file> --pretty prints a human-readable summary."""
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump({
            "profileVersion": "1.0.0",
            "person": {"id": "test-person"},
            "experiences": [],
            "skills": [],
            "education": [],
            "organizations": [],
            "professionalSummaries": [],
            "projects": [],
            "achievements": [],
            "evidence": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
        }),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-profile", str(profile_file), "--pretty"])

    assert result.exit_code == 0
    assert "Reasoning Report" in result.stdout
    assert "Engine Version:" in result.stdout
    assert "Profile ID:" in result.stdout
    assert "Total Findings:" in result.stdout


def test_analyze_profile_command_missing_file(tmp_path: Path) -> None:
    """careeros analyze-profile with a non-existent file exits with error."""
    missing = tmp_path / "does-not-exist.yaml"

    result = runner.invoke(app, ["analyze-profile", str(missing)])

    assert result.exit_code == 1
    assert "Failed to load" in result.stdout


def _write_profile(path: Path, *, person_id: str, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {
                    "id": person_id,
                    "names": [{"value": name, "usage": "professional"}],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_profiles_list_lists_profiles_sorted(tmp_path: Path) -> None:
    """careeros profiles list shows display name and id, sorted by name."""
    _write_profile(tmp_path / "person-zz-profile.yaml", person_id="person-zz", name="Zoe Example")
    _write_profile(tmp_path / "person-aa-profile.yaml", person_id="person-aa", name="Anna Example")
    _write_profile(tmp_path / "person-mm-profile.yaml", person_id="person-mm", name="Mia Example")

    result = runner.invoke(app, ["profiles", "list", "--profiles-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Available profiles" in result.stdout
    assert "Name" in result.stdout
    assert "Profile ID" in result.stdout
    assert result.stdout.index("Anna Example") < result.stdout.index("Mia Example")
    assert result.stdout.index("Mia Example") < result.stdout.index("Zoe Example")
    assert "person-aa" in result.stdout
    assert "person-mm" in result.stdout
    assert "person-zz" in result.stdout


def test_profiles_list_displays_id_without_profile_suffix(tmp_path: Path) -> None:
    """careeros profiles list shows ids addressable by csks query --profile."""
    _write_profile(
        tmp_path / "person-hechavarria-profile.yaml",
        person_id="person-hechavarria",
        name="Rene Hechavarria",
    )

    result = runner.invoke(app, ["profiles", "list", "--profiles-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Rene Hechavarria" in result.stdout
    assert "person-hechavarria" in result.stdout
    assert "person-hechavarria-profile" not in result.stdout


def test_profiles_list_includes_staging_profiles(tmp_path: Path) -> None:
    """careeros profiles list searches the same locations as the app, incl. staging."""
    _write_profile(
        tmp_path / "staging" / "person-staged-profile.yaml",
        person_id="person-staged",
        name="Staged Person",
    )
    _write_profile(
        tmp_path / "person-canon-profile.yaml",
        person_id="person-canon",
        name="Canon Person",
    )

    result = runner.invoke(app, ["profiles", "list", "--profiles-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "person-staged" in result.stdout
    assert "person-canon" in result.stdout


def test_profiles_list_empty_exits_nonzero(tmp_path: Path) -> None:
    """careeros profiles list exits non-zero with a friendly message when empty."""
    result = runner.invoke(app, ["profiles", "list", "--profiles-root", str(tmp_path)])

    assert result.exit_code == 1
    assert "No profiles found" in result.stdout


def test_profiles_list_help() -> None:
    """careeros profiles list exposes help text."""
    result = runner.invoke(app, ["profiles", "list", "--help"])

    assert result.exit_code == 0
    assert "List available profiles" in result.stdout
    assert "--profiles-root" in result.stdout
