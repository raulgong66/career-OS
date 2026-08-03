"""Tests for startup runtime configuration diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.runtime_config import (
    BACKEND_VERSION,
    RuntimeConfigurationError,
    render_configuration_banner,
    validate_runtime_config,
)


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("LLM_PROVIDER", "OLLAMA_MODEL", "OLLAMA_HOST", "OPENAI_API_KEY", "OPENAI_MODEL"):
        monkeypatch.delenv(key, raising=False)


def _write_env(tmp_path: Path, **values: str) -> Path:
    env_path = tmp_path / ".env"
    env_path.write_text("\n".join(f"{k}={v}" for k, v in values.items()), encoding="utf-8")
    return env_path


def test_valid_ollama_config(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path, LLM_PROVIDER="ollama", OLLAMA_MODEL="qwen2.5:3b")

    config = validate_runtime_config(env_path)

    assert config.env_loaded is True
    assert config.provider == "ollama"
    assert config.ollama_model == "qwen2.5:3b"
    assert config.openai_configured is False


def test_ollama_missing_model_fails(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path, LLM_PROVIDER="ollama")

    with pytest.raises(RuntimeConfigurationError, match="OLLAMA_MODEL is not configured"):
        validate_runtime_config(env_path)


def test_valid_openai_config(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path, LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test-secret")

    config = validate_runtime_config(env_path)

    assert config.provider == "openai"
    assert config.openai_configured is True
    assert config.ollama_model is None


def test_openai_missing_key_fails(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path, LLM_PROVIDER="openai")

    with pytest.raises(RuntimeConfigurationError, match="OPENAI_API_KEY is not configured"):
        validate_runtime_config(env_path)


def test_missing_provider_fails(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path)

    with pytest.raises(RuntimeConfigurationError, match="LLM_PROVIDER is not configured"):
        validate_runtime_config(env_path)


def test_unknown_provider_fails(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path, LLM_PROVIDER="anthropic")

    with pytest.raises(RuntimeConfigurationError, match="Unknown LLM_PROVIDER"):
        validate_runtime_config(env_path)


def test_missing_env_file_falls_back_to_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_env = tmp_path / "missing.env"
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")

    config = validate_runtime_config(missing_env)

    assert config.env_loaded is False
    assert config.provider == "ollama"
    assert config.ollama_model == "qwen2.5:3b"


def test_banner_reports_ollama_without_secrets() -> None:
    from api.runtime_config import RuntimeConfig

    config = RuntimeConfig(
        env_loaded=True,
        provider="ollama",
        ollama_model="qwen2.5:3b",
        openai_configured=False,
    )

    banner = render_configuration_banner(config)

    assert "CareerOS Platform Alpha" in banner
    assert "Environment      : .env loaded" in banner
    assert "LLM Provider     : ollama" in banner
    assert "Ollama Model     : qwen2.5:3b" in banner
    assert "OpenAI API Key   : not configured" in banner
    assert f"Backend Version  : {BACKEND_VERSION}" in banner


def test_banner_reports_openai_configured_and_never_prints_key() -> None:
    from api.runtime_config import RuntimeConfig

    config = RuntimeConfig(
        env_loaded=True,
        provider="openai",
        ollama_model=None,
        openai_configured=True,
    )

    banner = render_configuration_banner(config)

    assert "LLM Provider     : openai" in banner
    assert "Ollama Model     : n/a" in banner
    assert "OpenAI API Key   : configured" in banner
    assert "sk-" not in banner


def test_banner_reports_env_not_loaded() -> None:
    from api.runtime_config import RuntimeConfig

    config = RuntimeConfig(
        env_loaded=False,
        provider="ollama",
        ollama_model="qwen2.5:3b",
        openai_configured=False,
    )

    banner = render_configuration_banner(config)

    assert "Environment      : .env not loaded (using process environment)" in banner
