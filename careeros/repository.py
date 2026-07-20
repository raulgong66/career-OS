"""Filesystem-backed repository implementation for CareerOS entities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .exceptions import EntityNotFoundError, RepositoryError, ValidationError
from .models import EntityRecord
from .schema_loader import SchemaLoader
from .validator import EntityValidator


class FileSystemRepository:
    """A filesystem-based repository for persisting CareerOS entities."""

    def __init__(self, root_path: str | Path, schema_loader: SchemaLoader) -> None:
        """Initialize the repository.

        Args:
            root_path: Base directory used for storing entities.
            schema_loader: Loader used to resolve schemas for validation.
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.schema_loader = schema_loader
        self.validator = EntityValidator(schema_loader)

    def save(self, entity_type: str, entity: dict[str, Any]) -> EntityRecord:
        """Persist a new entity to disk.

        Args:
            entity_type: The schema entity type.
            entity: The entity data payload.

        Returns:
            The persisted entity record.

        Raises:
            ValidationError: If the entity fails schema validation.
            RepositoryError: If persistence fails.
        """
        validation_result = self.validator.validate_entity(entity, entity_type)
        if not validation_result.is_valid:
            raise ValidationError(
                f"Validation failed for {entity_type}",
                errors=validation_result.errors,
            )

        entity_id = str(entity.get("id") or entity.get("metadata", {}).get("id"))
        if not entity_id:
            raise RepositoryError("Entity payload is missing an identifier")

        record_path = self._entity_path(entity_type, entity_id)
        record_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._write_payload(record_path, entity)
        except OSError as exc:
            raise RepositoryError(f"Failed to write entity {entity_id}") from exc

        return EntityRecord(entity_type=entity_type, id=entity_id, data=entity)

    def get(self, entity_type: str, entity_id: str) -> EntityRecord:
        """Load an entity from disk by entity type and identifier."""
        record_path = self._entity_path(entity_type, entity_id)
        if not record_path.exists():
            raise EntityNotFoundError(f"Entity not found: {entity_type}/{entity_id}")

        try:
            payload = self._read_payload(record_path)
        except (json.JSONDecodeError, yaml.YAMLError, OSError) as exc:
            raise RepositoryError(f"Failed to load entity {record_path}") from exc

        return EntityRecord(entity_type=entity_type, id=entity_id, data=payload)

    def update(self, entity_type: str, entity_id: str, updates: dict[str, Any]) -> EntityRecord:
        """Update an existing entity on disk.

        Args:
            entity_type: Type of the entity to update.
            entity_id: Identifier of the entity to update.
            updates: Dictionary of fields to merge into the entity.

        Returns:
            The updated entity record.
        """
        existing = self.get(entity_type, entity_id).data
        merged = dict(existing)
        merged.update(updates)

        validation_result = self.validator.validate_entity(merged, entity_type)
        if not validation_result.is_valid:
            raise ValidationError(
                f"Validation failed for {entity_type}",
                errors=validation_result.errors,
            )

        record_path = self._entity_path(entity_type, entity_id)
        try:
            self._write_payload(record_path, merged)
        except OSError as exc:
            raise RepositoryError(f"Failed to update entity {entity_id}") from exc

        return EntityRecord(entity_type=entity_type, id=entity_id, data=merged)

    def delete(self, entity_type: str, entity_id: str) -> None:
        """Delete an entity from disk."""
        record_path = self._entity_path(entity_type, entity_id)
        if not record_path.exists():
            raise EntityNotFoundError(f"Entity not found: {entity_type}/{entity_id}")

        try:
            record_path.unlink()
        except OSError as exc:
            raise RepositoryError(f"Failed to delete entity {entity_id}") from exc

    def search(self, entity_type: str, entity_id: str) -> EntityRecord | None:
        """Return an entity if it exists, otherwise ``None``."""
        try:
            return self.get(entity_type, entity_id)
        except EntityNotFoundError:
            return None

    def _entity_path(self, entity_type: str, entity_id: str) -> Path:
        """Resolve the storage path for an entity."""
        return self.root_path / entity_type / f"{entity_id}.json"

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        """Serialize a payload to disk."""
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def _read_payload(self, path: Path) -> dict[str, Any]:
        """Load a payload from disk."""
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
