import yaml
from pathlib import Path

import pytest

from careeros.acquisition.yaml_writer import YamlWriter, YamlWriteError
from careeros.exceptions import CareerOSException, DuplicateProfileError, RepositoryError


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


def test_write_rejects_existing_target_path(tmp_path: Path) -> None:
    """A pre-existing output path is rejected as a duplicate profile."""
    output = tmp_path / "person-dup.yaml"
    output.write_text("existing: content\n", encoding="utf-8")
    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-dup"},
    }
    writer = YamlWriter()

    with pytest.raises(DuplicateProfileError) as excinfo:
        writer.write(profile, output)

    assert excinfo.value.person_id == "person-dup"
    assert excinfo.value.existing_path == str(output.resolve())
    assert "person-dup" in str(excinfo.value)


def test_write_rejects_duplicate_preserves_existing_content(tmp_path: Path) -> None:
    """The canonical existing profile is never overwritten by a duplicate write."""
    output = tmp_path / "person-keep.yaml"
    original = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-keep", "names": [{"value": "Original", "usage": "professional"}]},
    }
    YamlWriter().write(original, output)
    before = output.read_text(encoding="utf-8")

    duplicate = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-keep", "names": [{"value": "Replacement", "usage": "professional"}]},
    }
    with pytest.raises(DuplicateProfileError):
        YamlWriter().write(duplicate, output)

    assert output.read_text(encoding="utf-8") == before
    assert yaml.safe_load(output.read_text(encoding="utf-8")) == original


def test_write_rejects_duplicate_deterministically(tmp_path: Path) -> None:
    """Repeated duplicate writes raise the same error and never mutate the file."""
    output = tmp_path / "person-det.yaml"
    profile = {"profileVersion": "1.0.0", "person": {"id": "person-det"}}
    YamlWriter().write(profile, output)
    before = output.read_text(encoding="utf-8")

    writer = YamlWriter()
    for _ in range(2):
        with pytest.raises(DuplicateProfileError) as excinfo:
            writer.write(profile, output)
        assert excinfo.value.person_id == "person-det"
        assert excinfo.value.existing_path == str(output.resolve())

    assert output.read_text(encoding="utf-8") == before


def test_duplicate_profile_error_is_repository_error() -> None:
    """DuplicateProfileError fits the repository error hierarchy for API/CLI mapping."""
    error = DuplicateProfileError("person-x", "/profiles/person-x-profile.yaml")

    assert isinstance(error, DuplicateProfileError)
    assert isinstance(error, RepositoryError)
    assert isinstance(error, CareerOSException)
    assert error.person_id == "person-x"
    assert error.existing_path == "/profiles/person-x-profile.yaml"
