# ADR 006: AI Provider-Agnostic Foundation

## Status

Accepted (M1.13)

## Context

Core has two consumers that need LLM text generation today:

- **Acquisition extraction** (`careeros/acquisition/llm_extractor.py`) — turns raw resume/CV text into structured profile data.
- **CV generation** (`careeros/generators/markdown_cv.py`) — LLM-assisted tailoring of a CV against a job description (`CV_LLM_ENABLED`).

Historically each consumer made vendor HTTP calls directly and duplicated the same concerns: URL construction, request/response JSON shapes, headers, error handling, and env-based branching (`LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OLLAMA_HOST`, `OLLAMA_MODEL`). `markdown_cv.py` even contained three nearly identical methods (`_call_llm` / `_call_ollama` / `_call_openai`) plus an inline `httpx` import.

This violates the Core boundary rules from ADR-004: Core generators must not embed LLM/vendor code, and modules (Interview Intelligence — ADR-005, Career Analytics, Skill Gap Analysis) must be able to reuse AI-assisted generation without ever importing a vendor SDK.

The provider choice is configuration-driven (`.env`) and must remain so — no code-level or build-time provider selection. Testing AI-dependent paths also requires a deterministic, offline option.

## Decision

Introduce a **capability-oriented AI provider abstraction owned by Core**, in a dedicated `careeros/ai/` package:

1. **Single seam for all vendor code.** Only `careeros/ai/` imports `httpx` or knows vendor endpoints and JSON shapes. Core consumers, modules, and apps never do.
2. **Single capability interface.** `AIProvider.generate(prompt, *, temperature=0.1, timeout=60.0) -> str`. Prompt construction and response parsing are business logic and remain in the consumers (acquisition prompt/JSON schema, CV writer prompt/`{cv: ...}` parsing). The interface exposes only what is needed today — deliberately no `summarize`/`extract`/`classify` speculative capabilities.
3. **Configuration-driven selection.** `create_ai_provider()` reads `LLM_PROVIDER` (or an explicit `provider` argument) and returns the matching adapter. A missing provider raises `LLMConfigurationError("LLM_PROVIDER is not configured ...")`; an unknown provider raises `LLMConfigurationError("Unknown LLM_PROVIDER ...")`.
4. **Three implementations.** `OpenAIProvider` (chat completions), `OllamaProvider` (local `/api/generate`), and `MockAIProvider` — deterministic, offline, substring-keyed canned responses with call recording.
5. **Domain-typed errors.** `AIError` (call failure) and `AIResponseError` (unusable response) extend `CareerOSException`. Consumers map them to their own domain errors (`LLMExtractionError`; deterministic fallback in CV generation).
6. **Consumers hold the provider.** `LLMExtractor` (and its backward-compatible `OpenAILLMExtractor` / `OllamaLLMExtractor` subclasses and `create_llm_extractor()` factory) and `MarkdownCVGenerator` now take/use an `AIProvider` and call `generate()`.
7. **Apps reuse the Core list.** `api/runtime_config.py` imports `SUPPORTED_PROVIDERS` from `careeros.ai` instead of maintaining its own list, so the mock provider is configurable through the same validation/banner path.

## Architecture

```
careeros/ai/
├── base.py            — AIProvider interface, AIError, AIResponseError
├── factory.py         — SUPPORTED_PROVIDERS, create_ai_provider()
├── openai_provider.py — OpenAI chat-completions adapter
├── ollama_provider.py — Ollama /api/generate adapter
├── mock_provider.py   — deterministic offline adapter (no network)
└── __init__.py        — public facade (re-exported from careeros/)
```

Consumers (import only the interface + factory):

- `careeros/acquisition/llm_extractor.py` — `LLMExtractor`, `OpenAILLMExtractor`, `OllamaLLMExtractor`, `create_llm_extractor`.
- `careeros/generators/markdown_cv.py` — `MarkdownCVGenerator._call_llm`.

Apps: `api/runtime_config.py` — provider validation and banner for `openai`, `ollama`, and `mock`.

## Provider Model

| Provider | Selection | Adapter | Notes |
|---|---|---|---|
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY` | `OpenAIProvider` | `model` (default `gpt-4o`), `base_url`; missing key raises `LLMConfigurationError` |
| Ollama | `LLM_PROVIDER=ollama` | `OllamaProvider` | `host` (default `http://localhost:11434`), `model` (default `qwen2.5:3b`) |
| Mock | `LLM_PROVIDER=mock` | `MockAIProvider` | Deterministic, no secrets, no network; substring-keyed `responses`, `default_response`, `fail` mode, `.calls` recording |

Both OpenAI and Ollama adapters accept an optional `transport` (an `httpx.BaseTransport`) to enable offline testing via `httpx.MockTransport`.

## Capability Interface

```python
class AIProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 60.0,
    ) -> str:
        """Return the model's completion for a prompt. Raises AIError."""
```

Backward compatibility is preserved: `create_llm_extractor()` returns the same concrete extractor classes as before (`OpenAILLMExtractor` / `OllamaLLMExtractor`), `pipeline.llm_extractor` still accepts them, and all existing constructors keep their signatures.

## Testing Strategy

- **Selection.** `LLM_PROVIDER=openai|ollama|mock` → correct adapter; missing/unknown → `LLMConfigurationError` with the existing messages.
- **Mock contract.** Determinism, substring matching, default response, call recording, `fail` mode.
- **Interface contract.** A `MockAIProvider` drives the real `LLMExtractor.extract()` and `MarkdownCVGenerator.generate()` paths end-to-end.
- **Vendor adapters without network.** `OpenAIProvider` and `OllamaProvider` are exercised through `httpx.MockTransport`, asserting URL, request body, temperature, and response parsing (including `AIResponseError` on empty `choices` / empty response).
- **Result:** 24 new tests; full suite 644 passed (620 pre-existing + 24), frontend `npm run build` and `npm run lint` clean.

## Future Evolution

- **New providers** (Anthropic, Groq, Azure OpenAI, …) are a new adapter module + one factory entry; no consumer change.
- **New capabilities** beyond `generate` are added to the interface only when a real consumer needs them (per ADR, not speculatively).
- **Async variant** can be added when module work (e.g. Interview Intelligence simulation) requires concurrent completions.
- **Packaging** — `pyproject.toml` still lists `packages = ["careeros"]`; the `ai/` subpackage inherits this, but a `pip install .` smoke test should confirm subpackage inclusion before release.

## Consequences

**Positive:** a single, testable seam for all LLM access in Core; deterministic offline testing; future modules reuse the interface instead of copying vendor calls; `runtime_config` gets its provider list from one source; `httpx` no longer leaks into Core generators.

**Negative:** one more abstraction layer; adapters must normalize vendor quirks into `AIError`; the mock provider is only useful when consumers accept an injected provider (already true for both current consumers).
