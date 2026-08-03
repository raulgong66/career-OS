"""Profile loading helpers for CareerOS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

import yaml

from .exceptions import ValidationError
from .schema_loader import SchemaLoader
from .validator import EntityValidator


class ProfileLoader:
    """Load canonical CareerOS profile documents from disk."""

    def __init__(self, schema_loader: SchemaLoader) -> None:
        """Create a profile loader bound to a schema loader."""
        self.validator = EntityValidator(schema_loader)

    def load(self, file_path: Union[str, Path], *, validate: bool = True) -> dict[str, Any]:
        """Load a profile from a JSON or YAML file.

        Args:
            file_path: Path to the profile document.
            validate: Whether to validate the loaded profile against the profile schema.

        Returns:
            The loaded profile payload.

        Raises:
            ValidationError: If the file is missing, malformed, empty, not an object,
                or fails profile schema validation.
        """
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise ValidationError(f"Profile file not found: {path}")

        try:
            text = path.read_text(encoding="utf-8")
            payload = self._parse_payload(text, path)
        except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ValidationError(f"Failed to load profile file: {path}") from exc

        if not isinstance(payload, dict):
            raise ValidationError("Profile payload must be a JSON/YAML object")

        if validate:
            result = self.validator.validate_entity(payload, "profile")
            if not result.is_valid:
                raise ValidationError("Profile validation failed", errors=result.errors)

        return payload

    @staticmethod
    def _parse_payload(text: str, path: Path) -> Any:
        """Parse a profile payload based on file extension."""
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(text)
        return json.loads(text)
