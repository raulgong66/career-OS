"""Configuration-driven AI provider factory.

Changing providers requires changing configuration only. Core and modules
obtain providers through ``create_ai_provider`` and never construct vendor
clients themselves.
"""

from __future__ import annotations

import os

from careeros.exceptions import LLMConfigurationError

from .base import AIProvider
from .mock_provider import MockAIProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

SUPPORTED_PROVIDERS: tuple[str, ...] = ("openai", "ollama", "mock")


def create_ai_provider(provider: str | None = None) -> AIProvider:
    """Build the configured AI provider.

    Args:
        provider: Provider name. Defaults to the LLM_PROVIDER environment
            variable.

    Returns:
        The provider adapter for the configured provider.

    Raises:
        LLMConfigurationError: If no provider is configured or the provider is
            unknown.
    """
    name = (provider or os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if not name:
        raise LLMConfigurationError(
            "LLM_PROVIDER is not configured. Configure it in the .env file."
        )
    if name == "openai":
        return OpenAIProvider()
    if name == "ollama":
        return OllamaProvider()
    if name == "mock":
        return MockAIProvider()
    raise LLMConfigurationError(
        f"Unknown LLM_PROVIDER: {name}. Expected one of: {', '.join(SUPPORTED_PROVIDERS)}."
    )
