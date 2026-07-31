# CareerOS

CareerOS is a schema-driven toolkit for managing professional profile, application, and project data.

## Installation

```bash
python3 -m pip install -e .
```

## Usage

### CLI

```bash
careeros --help
careeros version
careeros doctor
careeros schemas list
careeros schemas info profile
careeros validate profile profiles/master-profile.yaml
careeros create company company.json
careeros show company company.json
careeros list company .
careeros search company name Example
```

### Configuration

Runtime settings are loaded from a `.env` file in the project root. Copy the example and adjust:

```bash
cp .env.example .env
```

Available variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | *(required)* | `ollama` or `openai` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Ollama model name |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `CV_LLM_ENABLED` | `false` | When `true`, CVs generated with a job description are tailored by the LLM provider |

A startup error is raised if `LLM_PROVIDER` is missing or invalid.

### API

```bash
cp .env.example .env
python3 -m uvicorn api.main:app --reload
```

Then open the docs at:

```text
http://127.0.0.1:8000/docs
```
