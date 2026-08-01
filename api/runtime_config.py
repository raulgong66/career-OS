"""Startup runtime configuration diagnostics for CareerOS.

Loads the project .env file, validates the required LLM configuration,
and renders a concise startup banner. No secrets are ever printed - only
whether optional secrets are configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from careeros.ai import SUPPORTED_PROVIDERS

BACKEND_VERSION = "1.0.0"


class RuntimeConfigurationError(Exception):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved and validated runtime configuration values."""

    env_loaded: bool
    provider: str
    ollama_model: Optional[str]
    openai_configured: bool


def resolve_env_path() -> Path:
    """Return the canonical path of the project .env file."""
    return Path(__file__).resolve().parents[1] / ".env"


def load_runtime_environment(env_path: Optional[Path] = None) -> bool:
    """Load the .env file into the environment.

    Returns True when the .env file existed and was loaded, False otherwise.
    Existing process environment variables are never overridden.
    """
    from dotenv import load_dotenv

    path = env_path or resolve_env_path()
    return load_dotenv(dotenv_path=path)


def _get_env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def validate_runtime_config(env_path: Optional[Path] = None) -> RuntimeConfig:
    """Load and validate the required runtime configuration.

    Raises RuntimeConfigurationError with a clear, human-readable message
    when a required variable is missing or an unknown provider is set.
    Does not silently fall back to another provider.
    """
    env_loaded = load_runtime_environment(env_path)

    provider = _get_env("LLM_PROVIDER").lower()
    if not provider:
        raise RuntimeConfigurationError(
            "LLM_PROVIDER is not configured. Add 'LLM_PROVIDER=<provider>' "
            "to the .env file."
        )
    if provider not in SUPPORTED_PROVIDERS:
        raise RuntimeConfigurationError(
            f"Unknown LLM_PROVIDER: {provider!r}. "
            f"Expected one of: {', '.join(SUPPORTED_PROVIDERS)}."
        )

    openai_configured = bool(_get_env("OPENAI_API_KEY"))

    if provider == "mock":
        return RuntimeConfig(
            env_loaded=env_loaded,
            provider="mock",
            ollama_model=None,
            openai_configured=False,
        )

    if provider == "ollama":
        model = _get_env("OLLAMA_MODEL")
        if not model:
            raise RuntimeConfigurationError(
                "OLLAMA_MODEL is not configured. Add 'OLLAMA_MODEL=<model>' "
                "(e.g. OLLAMA_MODEL=qwen2.5:3b) to the .env file."
            )
        return RuntimeConfig(
            env_loaded=env_loaded,
            provider="ollama",
            ollama_model=model,
            openai_configured=openai_configured,
        )

    if not openai_configured:
        raise RuntimeConfigurationError(
            "OPENAI_API_KEY is not configured. Add 'OPENAI_API_KEY=sk-...' "
            "to the .env file."
        )

    model = _get_env("OLLAMA_MODEL") or None
    return RuntimeConfig(
        env_loaded=env_loaded,
        provider="openai",
        ollama_model=model,
        openai_configured=True,
    )


def render_configuration_banner(config: RuntimeConfig) -> str:
    """Render the startup configuration summary as a string."""
    env_status = ".env loaded" if config.env_loaded else ".env not loaded (using process environment)"
    openai_status = "configured" if config.openai_configured else "not configured"
    separator = "-" * 50
    lines = [
        separator,
        "CareerOS Platform Alpha",
        "Configuration",
        separator,
        f"Environment      : {env_status}",
        f"LLM Provider     : {config.provider}",
        f"Ollama Model     : {config.ollama_model or 'n/a'}",
        f"OpenAI API Key   : {openai_status}",
        f"Backend Version  : {BACKEND_VERSION}",
        separator,
    ]
    return "\n".join(lines)


def print_configuration_banner(config: RuntimeConfig) -> None:
    """Print the startup configuration summary exactly once."""
    print(render_configuration_banner(config))
