"""Tests that checkpoint model output conforms to schemas/checkpoint.schema.json."""

from __future__ import annotations

from pathlib import Path

from careeros.models import ValidationResult
from careeros.schema_loader import SchemaLoader
from careeros.validator import EntityValidator

from test_checkpoint_cli import make_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_checkpoint_schema_is_valid_draft_2020_12() -> None:
    schema = SchemaLoader(REPO_ROOT / "schemas").load_schema("checkpoint")
    assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12/")
    assert schema["$id"] == "https://career-os.local/schemas/checkpoint.schema.json"


def test_model_conforms_to_schema() -> None:
    validator = EntityValidator(SchemaLoader(REPO_ROOT / "schemas"))
    result: ValidationResult = validator.validate_entity(make_checkpoint().to_dict(), "checkpoint")
    assert result.is_valid, result.errors