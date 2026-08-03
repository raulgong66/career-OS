import yaml
from pathlib import Path

import pytest

from careeros.acquisition.yaml_writer import YamlWriter, YamlWriteError


def test_write_creates_yaml_file(tmp_path: Path) -> None:
    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-write-test"},
    }
    output = tmp_path / "output.yaml"
    writer = YamlWriter()
    result = writer.write(profile, output)

    assert result == output.resolve()
    assert output.exists()
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded["profileVersion"] == "1.0.0"
    assert loaded["person"]["id"] == "person-write-test"


def test_write_default_output_path(tmp_path: Path) -> None:
    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-default-path"},
    }
    writer = YamlWriter()
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        result = writer.write(profile)

    assert result.name == "person-default-path-profile.yaml"
    # Default output is under profiles/staging/ for staged review
    assert result.parent.name == "staging"
    assert result.parent.parent.name == "profiles"
    assert result.exists()
    loaded = yaml.safe_load(result.read_text(encoding="utf-8"))
    assert loaded["person"]["id"] == "person-default-path"


def test_write_default_fallback_for_unknown_id(tmp_path: Path) -> None:
    profile = {"profileVersion": "1.0.0", "person": {}}
    writer = YamlWriter()

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        result = writer.write(profile)

    assert result.name == "unknown-profile.yaml"


def test_write_preserves_yaml_structure(tmp_path: Path) -> None:
    profile = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-structure",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
        },
        "experiences": [],
        "skills": [],
    }
    output = tmp_path / "structure.yaml"
    writer = YamlWriter()
    writer.write(profile, output)

    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded == profile


def test_write_uses_person_id_for_default_filename(tmp_path: Path) -> None:
    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-custom"},
    }
    writer = YamlWriter()
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        result = writer.write(profile)

    assert result.name == "person-custom-profile.yaml"
