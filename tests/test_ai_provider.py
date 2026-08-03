"""Tests for the AI provider-agnostic foundation (M1.13).

Covers provider selection, the deterministic mock provider, capability
interface behavior, and the existing OpenAI/Ollama implementations exercised
through the new interface (using httpx.MockTransport, so no network access).
"""

from __future__ import annotations

import json

import httpx
import pytest

from careeros.ai import (
    AIError,
    AIProvider,
    AIResponseError,
    MockAIProvider,
    OllamaProvider,
    OpenAIProvider,
    SUPPORTED_PROVIDERS,
    create_ai_provider,
)
from careeros.exceptions import LLMConfigurationError
from careeros.acquisition.llm_extractor import (
    LLMExtractor,
    OllamaLLMExtractor,
    OpenAILLMExtractor,
    create_llm_extractor,
)
from careeros.export_contract import ExportContract
from careeros.generators import MarkdownCVGenerator


# --------------------------------------------------------------------------
# Provider selection
# --------------------------------------------------------------------------


def test_create_ai_provider_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    provider = create_ai_provider()
    assert isinstance(provider, MockAIProvider)


def test_create_ai_provider_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert isinstance(create_ai_provider(), OpenAIProvider)


def test_create_ai_provider_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert isinstance(create_ai_provider(), OllamaProvider)


def test_create_ai_provider_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(LLMConfigurationError, match="LLM_PROVIDER is not configured"):
        create_ai_provider()


def test_create_ai_provider_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    with pytest.raises(LLMConfigurationError, match="Unknown LLM_PROVIDER"):
        create_ai_provider()


def test_supported_providers() -> None:
    assert set(SUPPORTED_PROVIDERS) == {"openai", "ollama", "mock"}


def test_create_llm_extractor_selects_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert isinstance(create_llm_extractor(), OpenAILLMExtractor)


def test_create_llm_extractor_selects_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert isinstance(create_llm_extractor(), OllamaLLMExtractor)


def test_create_llm_extractor_selects_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    extractor = create_llm_extractor()
    assert isinstance(extractor, LLMExtractor)
    assert isinstance(extractor.provider, MockAIProvider)


# --------------------------------------------------------------------------
# Mock provider behavior
# --------------------------------------------------------------------------


def test_mock_provider_is_deterministic() -> None:
    provider = MockAIProvider(default_response="hello")
    assert provider.generate("x") == "hello"
    assert provider.generate("x") == "hello"


def test_mock_provider_substring_responses() -> None:
    provider = MockAIProvider(
        responses={"role=user": "A", "the job": "B"},
        default_response="C",
    )
    assert provider.generate("messages role=user now") == "A"
    assert provider.generate("the job description") == "B"
    assert provider.generate("unrelated") == "C"


def test_mock_provider_records_calls() -> None:
    provider = MockAIProvider()
    provider.generate("first")
    provider.generate("second", temperature=0.5)
    assert provider.calls == ["first", "second"]


def test_mock_provider_can_fail() -> None:
    provider = MockAIProvider(fail=True)
    with pytest.raises(AIError, match="mock provider failure"):
        provider.generate("x")


def test_mock_provider_is_interface_compliant() -> None:
    provider = MockAIProvider()
    assert isinstance(provider, AIProvider)
    assert provider.name == "mock"


# --------------------------------------------------------------------------
# Interface behavior (generate capability through Core consumers)
# --------------------------------------------------------------------------


def test_llm_extractor_uses_provider_generate_capability() -> None:
    canned = {
        "person": {"id": "person-x", "fullName": "X Sample"},
        "experiences": [
            {
                "id": "exp-1",
                "organization": "ACME",
                "title": "Engineer",
                "technologies": ["AWS"],
            }
        ],
        "skills": [{"name": "AWS", "category": "Cloud Platform"}],
        "education": [],
    }
    provider = MockAIProvider(responses={"extractor": json.dumps(canned)})
    extractor = LLMExtractor(provider=provider)

    result = extractor.extract("some resume text")

    assert len(provider.calls) == 1
    assert result.person.full_name == "X Sample"
    assert result.experiences[0].organization == "ACME"
    assert result.skills[0].name == "AWS"


def test_markdown_cv_generator_uses_provider_generate_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CV_LLM_ENABLED", "true")
    canned = json.dumps({"cv": "# Raul Gongora\n\n## Professional Summary\n\nTailored."})
    provider = MockAIProvider(responses={"CV writer": canned})
    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="artf-cv-1",
        artifact_type="CV",
        person={
            "id": "person-x",
            "names": [{"value": "Raul Gongora", "usage": "professional"}],
            "email": "raul@example.com",
        },
        artifact={"id": "artf-cv-1", "artifactType": "CV"},
        sources=[],
        job_description="Senior Kubernetes engineer",
    )

    generator = MarkdownCVGenerator(provider=provider)
    output = generator.generate(contract)

    assert len(provider.calls) == 1
    assert "CV writer" in provider.calls[0]
    assert output.strip() == "# Raul Gongora\n\n## Professional Summary\n\nTailored."


def test_markdown_cv_generator_falls_back_to_deterministic_on_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CV_LLM_ENABLED", "true")
    contract = ExportContract(
        profile_version="1.0.0",
        artifact_id="artf-cv-1",
        artifact_type="CV",
        person={"id": "person-x", "names": [{"value": "Raul Gongora", "usage": "professional"}]},
        artifact={"id": "artf-cv-1", "artifactType": "CV"},
        sources=[],
        job_description="Senior Kubernetes engineer",
    )

    generator = MarkdownCVGenerator(provider=MockAIProvider(fail=True))
    output = generator.generate(contract)

    assert output.startswith("# Raul Gongora")


# --------------------------------------------------------------------------
# OpenAI implementation through the new interface (no network)
# --------------------------------------------------------------------------


def test_openai_provider_generate_via_mock_transport() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi from openai"}}]})

    provider = OpenAIProvider(api_key="sk-test", transport=httpx.MockTransport(handler))

    text = provider.generate("say hi", temperature=0.5)

    assert text == "hi from openai"
    assert "https://api.openai.com/v1/chat/completions" in str(captured["url"])
    body = captured["json"]
    assert body["model"] == "gpt-4o"
    assert body["messages"] == [{"role": "user", "content": "say hi"}]
    assert body["temperature"] == 0.5


def test_openai_provider_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="OpenAI API key is required"):
        OpenAIProvider(api_key=None)


def test_openai_provider_no_choices_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = OpenAIProvider(api_key="sk-test", transport=httpx.MockTransport(handler))
    with pytest.raises(AIResponseError, match="no choices"):
        provider.generate("x")


def test_openai_extractor_through_interface() -> None:
    canned = {
        "person": {"id": "person-y", "fullName": "Y Person"},
        "experiences": [],
        "skills": [],
        "education": [],
    }
    raw = json.dumps(canned)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": raw}}]})

    extractor = OpenAILLMExtractor(
        api_key="sk-test", provider=OpenAIProvider(api_key="sk-test", transport=httpx.MockTransport(handler))
    )
    result = extractor.extract("resume")
    assert result.person.full_name == "Y Person"


# --------------------------------------------------------------------------
# Ollama implementation through the new interface (no network)
# --------------------------------------------------------------------------


def test_ollama_provider_generate_via_mock_transport() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "hi from ollama"})

    provider = OllamaProvider(host="http://localhost:11434", transport=httpx.MockTransport(handler))

    text = provider.generate("hello")

    assert text == "hi from ollama"
    assert str(captured["url"]).endswith("/api/generate")
    assert captured["json"]["model"] == "qwen2.5:3b"


def test_ollama_provider_empty_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": ""})

    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(AIResponseError, match="empty response"):
        provider.generate("x")


def test_ollama_extractor_preserves_host_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = OllamaLLMExtractor(host="http://192.168.1.100:11434", model="llama3.2:3b")
    assert extractor.host == "http://192.168.1.100:11434"
    assert extractor.model == "llama3.2:3b"
