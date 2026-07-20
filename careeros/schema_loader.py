"""Schema discovery and loading helpers for CareerOS."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .exceptions import SchemaLoadError


class SchemaLoader:
    """Discover, cache, and load JSON Schema documents for CareerOS entities."""

    def __init__(self, schema_root: str | Path | None = None) -> None:
        """Initialize the loader with a schema directory.

        Args:
            schema_root: Path to the directory containing schema files.
        """
        self.schema_root = Path(schema_root or self._default_schema_root())
        if not self.schema_root.exists():
            raise SchemaLoadError(f"Schema directory does not exist: {self.schema_root}")
        self._schema_cache: dict[str, dict[str, Any]] = {}
        self._discover_schemas()

    @staticmethod
    def _default_schema_root() -> Path:
        """Resolve the default schema location relative to this package."""
        return Path(__file__).resolve().parents[1] / "schemas"

    def _discover_schemas(self) -> None:
        """Discover all schema files in the configured schema directory."""
        for schema_path in sorted(self.schema_root.glob("*.schema.json")):
            entity_name = schema_path.stem.removesuffix(".schema")
            self._schema_cache[entity_name] = {}

    def load_schema(self, entity_name: str) -> dict[str, Any]:
        """Load a schema by entity name.

        Args:
            entity_name: The entity name without the ``.schema.json`` suffix.

        Returns:
            The loaded schema document.

        Raises:
            SchemaLoadError: If the schema cannot be found or parsed.
        """
        normalized_name = entity_name.strip().lower()
        schema_path = self.schema_root / f"{normalized_name}.schema.json"
        if not schema_path.exists():
            raise SchemaLoadError(f"Unable to locate schema for entity: {entity_name}")

        if normalized_name in self._schema_cache and self._schema_cache[normalized_name]:
            return self._schema_cache[normalized_name]

        try:
            with schema_path.open("r", encoding="utf-8") as handle:
                schema = json.load(handle)
        except json.JSONDecodeError as exc:
            raise SchemaLoadError(f"Failed to parse schema file: {schema_path}") from exc

        self._schema_cache[normalized_name] = schema
        return schema

    def discover_entity_names(self) -> list[str]:
        """Return the discovered entity names."""
        return sorted(self._schema_cache.keys())

    def resolve_relative_schema_path(self, schema: dict[str, Any], base_path: str | Path) -> str:
        """Resolve a relative schema path against the configured schema root.

        Args:
            schema: The schema document containing a ``$ref`` value.
            base_path: The base path used for resolution.

        Returns:
            A resolved schema path or the original value when it is not relative.
        """
        if not isinstance(schema, dict):
            return str(base_path)
        for _, value in schema.items():
            if isinstance(value, str) and value.startswith("#"):
                continue
            if isinstance(value, str) and value.startswith("./"):
                return str((self.schema_root / value).resolve())
        return str(base_path)
