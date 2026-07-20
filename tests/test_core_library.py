import json
from pathlib import Path

import pytest
import yaml

from careeros.exceptions import (
    EntityNotFoundError,
    RepositoryError,
    SchemaLoadError,
    ValidationError,
)
from careeros.models import EntityRecord, ValidationResult
from careeros.repository import FileSystemRepository
from careeros.schema_loader import SchemaLoader
from careeros.validator import EntityValidator


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_schema_loader_discovers_and_loads_schemas(repo_root: Path) -> None:
    loader = SchemaLoader(repo_root / "schemas")
    schema = loader.load_schema("profile")

    assert schema["title"] == "CareerOS Canonical Profile"


def test_schema_loader_raises_for_unknown_schema(repo_root: Path) -> None:
    loader = SchemaLoader(repo_root / "schemas")

    with pytest.raises(SchemaLoadError):
        loader.load_schema("does-not-exist")


def test_validator_returns_structured_results(repo_root: Path) -> None:
    loader = SchemaLoader(repo_root / "schemas")
    validator = EntityValidator(loader)

    valid_profile = {
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

    result = validator.validate_entity(valid_profile, "profile")

    assert result.is_valid
    assert result.errors == []


def test_validator_reports_validation_errors(repo_root: Path) -> None:
    loader = SchemaLoader(repo_root / "schemas")
    validator = EntityValidator(loader)

    invalid_profile = {"person": {}}  # Missing required profileVersion and person.id

    result = validator.validate_entity(invalid_profile, "profile")

    assert not result.is_valid
    assert len(result.errors) >= 1


def test_repository_round_trip(tmp_path: Path, repo_root: Path) -> None:
    repository = FileSystemRepository(tmp_path, SchemaLoader(repo_root / "schemas"))
    entity = {
        "id": "entity-1",
        "name": "Example company",
        "metadata": {
            "id": "entity-1",
            "version": "1.0.0",
            "status": "ACTIVE",
        },
    }

    saved = repository.save("company", entity)

    assert saved.id == "entity-1"
    assert repository.get("company", "entity-1") is not None


def test_repository_update_and_delete(tmp_path: Path, repo_root: Path) -> None:
    repository = FileSystemRepository(tmp_path, SchemaLoader(repo_root / "schemas"))
    entity = {
        "id": "entity-2",
        "name": "Example company",
        "metadata": {
            "id": "entity-2",
            "version": "1.0.0",
            "status": "ACTIVE",
        },
    }

    repository.save("company", entity)
    updated = repository.update("company", "entity-2", {"name": "Updated company"})

    assert updated.data["name"] == "Updated company"

    repository.delete("company", "entity-2")

    with pytest.raises(EntityNotFoundError):
        repository.get("company", "entity-2")


def test_repository_search_by_id(tmp_path: Path, repo_root: Path) -> None:
    repository = FileSystemRepository(tmp_path, SchemaLoader(repo_root / "schemas"))
    entity = {
        "id": "entity-3",
        "name": "Example company",
        "metadata": {
            "id": "entity-3",
            "version": "1.0.0",
            "status": "ACTIVE",
        },
    }

    repository.save("company", entity)

    found = repository.search("company", "entity-3")
    assert found is not None
    assert found.id == "entity-3"


def test_repository_rejects_invalid_entity(tmp_path: Path, repo_root: Path) -> None:
    repository = FileSystemRepository(tmp_path, SchemaLoader(repo_root / "schemas"))

    with pytest.raises(ValidationError):
        repository.save("company", {"name": "Invalid company"})


def test_repository_raises_for_missing_entity(tmp_path: Path, repo_root: Path) -> None:
    repository = FileSystemRepository(tmp_path, SchemaLoader(repo_root / "schemas"))

    with pytest.raises(EntityNotFoundError):
        repository.get("company", "missing")


def test_models_are_lightweight_and_serializable() -> None:
    record = EntityRecord(entity_type="company", id="abc", data={"name": "Example"})

    assert record.entity_type == "company"
    assert record.id == "abc"
    assert record.data["name"] == "Example"

    payload = record.to_dict()
    assert payload["entity_type"] == "company"


def test_validation_result_serializes() -> None:
    result = ValidationResult(is_valid=False, errors=[{"path": "$", "message": "bad"}])

    payload = result.to_dict()
    assert payload["is_valid"] is False
    assert payload["errors"][0]["path"] == "$"
