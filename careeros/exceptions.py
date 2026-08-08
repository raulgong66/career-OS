"""Custom exceptions for the CareerOS core library."""

from __future__ import annotations


class CareerOSException(Exception):
    """Base exception for all CareerOS core errors."""


class SchemaLoadError(CareerOSException):
    """Raised when a schema cannot be discovered or loaded."""


class ValidationError(CareerOSException):
    """Raised when an entity does not satisfy its schema."""

    def __init__(self, message: str, errors: list[dict[str, object]] | None = None) -> None:
        """Initialize the exception with a summary and optional structured errors."""
        super().__init__(message)
        self.errors = errors or []


class RepositoryError(CareerOSException):
    """Raised when repository operations fail."""


class EntityNotFoundError(RepositoryError):
    """Raised when a requested entity cannot be found."""


class DuplicateProfileError(RepositoryError):
    """Raised when a profile with the same person.id already exists."""

    def __init__(self, person_id: str, existing_path: str) -> None:
        """Initialize with the conflicting profile id and its existing file path."""
        super().__init__(
            f"A profile with person.id '{person_id}' already exists at {existing_path}."
        )
        self.person_id = person_id
        self.existing_path = existing_path


class LLMConfigurationError(CareerOSException):
    """Raised when LLM provider configuration is missing or invalid."""
