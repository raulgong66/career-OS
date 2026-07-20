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
