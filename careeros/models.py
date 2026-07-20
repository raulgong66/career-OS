"""Lightweight models used by the CareerOS core library."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    """Structured validation outcome for an entity."""

    is_valid: bool
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the validation result to a serializable dictionary."""
        return {"is_valid": self.is_valid, "errors": self.errors}


@dataclass(slots=True)
class EntityRecord:
    """A lightweight record for storing an entity and its payload."""

    entity_type: str
    id: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the record to a serializable dictionary."""
        return {"entity_type": self.entity_type, "id": self.id, "data": self.data}
