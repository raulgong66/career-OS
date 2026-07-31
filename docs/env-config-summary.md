# Runtime Configuration (`.env`) — Summary of Changes

## Problem
The CV import pipeline required `OPENAI_API_KEY` even when using Ollama, because `LLM_PROVIDER` defaulted to `"openai"` when unset. Setting it via PowerShell `$env:` variables was ephemeral — lost on every process restart and `--reload` cycle.

## Solution

### 1. `.env`-based configuration
- Added `python-dotenv` dependency (`pyproject.toml`)
- Created `.env` with `LLM_PROVIDER=ollama`, `OLLAMA_HOST`, `OLLAMA_MODEL=qwen2.5:3b`
- Created `.env.example` as a template (committed to git)
- Added `.env` to `.gitignore`

### 2. Auto-load on startup
- `api/main.py`: `load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")` — explicit path, not CWD-dependent
- `careeros_cli/main.py`: same call for CLI entry point

### 3. Removed implicit OpenAI fallback
- `create_llm_extractor()` in `careeros/acquisition/llm_extractor.py`: removed `default="openai"` → raises `LLMConfigurationError` if unset
- `OLLAMA_MODEL` default changed from `"qwen3:4b"` to `"qwen2.5:3b"`

### 4. JSON parser hardening
- `parse_response()` in `llm_extractor.py`: added fallback that strips trailing commas before `]`/`}` — Ollama `qwen2.5:3b` sometimes outputs them

### 5. Test updates
- Added `test_create_extractor_no_provider` — confirms clear error when `LLM_PROVIDER` missing
- Updated `test_create_openai_extractor_when_ollama_not_set` to set `LLM_PROVIDER=openai`
- Updated default model assertion from `qwen3:4b` to `qwen2.5:3b`
- 567 tests pass

### 6. Documentation
- `README.md` updated with `.env` setup instructions and variable table
- `docs/env-config-summary.md` (this file)

## Verification
- CV import via `/profiles/import` returns **201 Created** using Ollama, no manual env vars
- Survives backend restart and `--reload` cycles

## Files Changed
- `api/main.py` — added `load_dotenv()`
- `careeros_cli/main.py` — added `load_dotenv()`
- `careeros/acquisition/llm_extractor.py` — removed OpenAI default, trailing comma fix
- `pyproject.toml` — added `python-dotenv`
- `.env.example` — new file (template)
- `.gitignore` — added `.env`
- `README.md` — updated startup instructions
- `tests/test_acquisition_integration.py` — updated tests
- `frontend/vite.config.ts` — temporary port workaround (8000→8001 for zombie socket)
