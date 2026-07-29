"""Validation helpers for CareerOS entities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .exceptions import ValidationError
from .models import ValidationResult
from .schema_loader import SchemaLoader


class EntityValidator:
    """Validate CareerOS entities against their JSON Schema definitions."""

    def __init__(self, schema_loader: SchemaLoader) -> None:
        """Create a validator bound to a schema loader."""
        self.schema_loader = schema_loader

    def validate_entity(self, entity: Any, entity_name: str) -> ValidationResult:
        """Validate a Python object against the schema for an entity.

        Args:
            entity: The entity payload to validate.
            entity_name: The entity schema name.

        Returns:
            A structured validation result.

        Raises:
            ValidationError: If the entity cannot be validated because the schema is missing.
        """
        schema = self.schema_loader.load_schema(entity_name)
        registry = self._build_registry()
        validator = Draft202012Validator(schema, registry=registry)
        errors = [
            {
                "path": self._format_path(list(error.absolute_path)),
                "message": error.message,
                "schema_path": list(error.absolute_schema_path),
            }
            for error in validator.iter_errors(entity)
        ]
        return ValidationResult(is_valid=not errors, errors=errors)

    def _build_registry(self) -> Registry:
        """Build a registry that maps local schema IDs to resident schema documents."""
        registry: Registry = Registry()
        for entity_name in self.schema_loader.discover_entity_names():
            schema = self.schema_loader.load_schema(entity_name)
            schema_id = schema.get("$id") or f"https://career-os.local/schemas/{entity_name}.schema.json"
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
        return registry

    @staticmethod
    def validate_file(file_path: Union[str, Path], entity_name: str, schema_loader: SchemaLoader) -> ValidationResult:
        """Load and validate an entity from a JSON or YAML file."""
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise ValidationError(f"File not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            text = handle.read()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = yaml.safe_load(text)

        validator = EntityValidator(schema_loader)
        return validator.validate_entity(payload, entity_name)

    @staticmethod
    def _format_path(path: list[Union[str, int]]) -> str:
        """Render an error path in a stable, human-readable format."""
        if not path:
            return "$"
        rendered = "$"
        for part in path:
            if isinstance(part, int):
                rendered += f"[{part}]"
            else:
                rendered += f".{part}" if rendered != "$" else f".{part}"
        return rendered
