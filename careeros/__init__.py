"""Core library for CareerOS."""

from .exceptions import (
    CareerOSException,
    EntityNotFoundError,
    RepositoryError,
    SchemaLoadError,
    ValidationError,
)
from .models import EntityRecord, ValidationResult
from .repository import FileSystemRepository
from .schema_loader import SchemaLoader
from .validator import EntityValidator

__all__ = [
    "CareerOSException",
    "EntityNotFoundError",
    "EntityRecord",
    "EntityValidator",
    "FileSystemRepository",
    "RepositoryError",
    "SchemaLoader",
    "SchemaLoadError",
    "ValidationError",
    "ValidationResult",
]
