from pathlib import Path

import pytest


@pytest.fixture
def csks_sample_repo(tmp_path: Path) -> Path:
    """Create a small repository used by CSKS tests.

    The fixture repository exercises every extractor and every entity type:
    Python classes/functions, reasoning rules, generators, FastAPI endpoints,
    Typer commands, domain map + mermaid graph, ADRs, JSON schemas, and TOML
    configuration. Tests assert against the observed graph using dynamic
    discovery, never hardcoded counts.
    """
    repo = tmp_path / "csks-sample"
    repo.mkdir()

    (repo / "careeros").mkdir()
    (repo / "careeros" / "reasoning").mkdir()
    (repo / "careeros" / "reasoning" / "rules").mkdir()
    (repo / "careeros" / "generators").mkdir()
    (repo / "careeros" / "services").mkdir()
    (repo / "careeros_cli").mkdir()
    (repo / "api").mkdir()
    (repo / "docs" / "architecture").mkdir(parents=True)
    (repo / "docs" / "adr").mkdir(parents=True)
    (repo / "schemas").mkdir()
    (repo / "tests").mkdir()

    (repo / "careeros" / "widgets.py").write_text(
        "from typing import Protocol\n"
        "\n"
        "\n"
        "class Widget(Protocol):\n"
        "    def render(self) -> str:\n"
        "        ...\n"
        "\n"
        "\n"
        "class ConcreteWidget:\n"
        "    def render(self) -> str:\n"
        "        return 'widget'\n"
        "\n"
        "\n"
        "def make_widget() -> ConcreteWidget:\n"
        "    return ConcreteWidget()\n",
        encoding="utf-8",
    )

    (repo / "careeros" / "profile_loader.py").write_text(
        "from careeros.widgets import ConcreteWidget, make_widget\n"
        "\n"
        "\n"
        "class ProfileLoader:\n"
        "    def load_profile(self) -> str:\n"
        "        return 'profile'\n"
        "\n"
        "\n"
        "def load_default_profile() -> str:\n"
        "    widget = make_widget()\n"
        "    return widget.render()\n",
        encoding="utf-8",
    )

    (repo / "careeros" / "reasoning" / "rules" / "skill_rules.py").write_text(
        "from typing import Any\n"
        "\n"
        "\n"
        "class Rule:\n"
        "    pass\n"
        "\n"
        "\n"
        "class TotalYearsExperienceRule(Rule):\n"
        "    def evaluate(self, data: dict[str, Any]) -> bool:\n"
        "        return True\n",
        encoding="utf-8",
    )

    (repo / "careeros" / "generators" / "markdown_generator.py").write_text(
        "class MarkdownGenerator:\n"
        "    def generate(self) -> str:\n"
        "        return '# CV'\n",
        encoding="utf-8",
    )

    (repo / "careeros" / "services" / "summarizer.py").write_text(
        "from careeros.profile_loader import ProfileLoader\n"
        "\n"
        "\n"
        "def summarize() -> str:\n"
        "    loader = ProfileLoader()\n"
        "    return loader.load_profile()\n",
        encoding="utf-8",
    )

    (repo / "api" / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "\n"
        "@app.get('/health')\n"
        "def health() -> dict:\n"
        "    return {'status': 'ok'}\n"
        "\n"
        "\n"
        "@app.get('/profiles')\n"
        "def list_profiles() -> list:\n"
        "    return []\n"
        "\n"
        "\n"
        "@app.get('/profiles/{profile_id}')\n"
        "def get_profile(profile_id: str) -> dict:\n"
        "    return {'id': profile_id}\n",
        encoding="utf-8",
    )

    (repo / "careeros_cli" / "main.py").write_text(
        "import typer\n"
        "\n"
        "\n"
        "app = typer.Typer()\n"
        "\n"
        "\n"
        "@app.command('version')\n"
        "def version() -> None:\n"
        "    print('1.0.0')\n"
        "\n"
        "\n"
        "@app.command('validate')\n"
        "def validate() -> None:\n"
        "    print('valid')\n",
        encoding="utf-8",
    )

    (repo / "docs" / "architecture" / "02-domain-map.md").write_text(
        "# Domain Map\n"
        "\n"
        "## Domains\n"
        "\n"
        "### 1. Profile Management\n"
        "Manages the canonical profile.\n"
        "\n"
        "### 2. Knowledge Graph\n"
        "Stores structured knowledge.\n"
        "\n"
        "### 3. Schema Foundation\n"
        "Defines schemas.\n"
        "\n"
        "```mermaid\n"
        "graph LR\n"
        '  Profile["Profile Management"] --> Schema["Schema Foundation"]\n'
        '  KG["Knowledge Graph"] --> Profile["Profile Management"]\n'
        "```\n"
        "\n"
        "| Domain | Status |\n"
        "| --- | --- |\n"
        "| Profile Management | Core |\n"
        "| Knowledge Graph | Core |\n",
        encoding="utf-8",
    )

    (repo / "docs" / "adr" / "0001-storage.md").write_text(
        "# ADR 0001: Storage Backend\n"
        "\n"
        "## Status\n"
        "\n"
        "Accepted\n"
        "\n"
        "## Context\n"
        "\n"
        "We need durable storage.\n"
        "\n"
        "## Decision\n"
        "\n"
        "Use the filesystem.\n",
        encoding="utf-8",
    )

    (repo / "docs" / "adr" / "0002-llm.md").write_text(
        "---\n"
        "title: LLM Provider Abstraction\n"
        "status: Proposed\n"
        "number: 2\n"
        "---\n"
        "\n"
        "# ADR 0002: LLM Provider Abstraction\n",
        encoding="utf-8",
    )

    (repo / "schemas" / "skill.schema.json").write_text(
        "{\n"
        "  \"title\": \"Skill\",\n"
        "  \"type\": \"object\",\n"
        "  \"required\": [\"name\"],\n"
        "  \"properties\": {\n"
        "    \"name\": {\"type\": \"string\"},\n"
        "    \"level\": {\"type\": \"string\", \"enum\": [\"beginner\", \"expert\"]}\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    (repo / "schemas" / "role.schema.json").write_text(
        "{\n"
        "  \"title\": \"Role\",\n"
        "  \"type\": \"object\",\n"
        "  \"properties\": {\n"
        "    \"skill\": {\"$ref\": \"./skill.schema.json\"}\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    (repo / "pyproject.toml").write_text(
        "[project]\n"
        'name = "csks-sample"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        'pythonpath = ["."]\n',
        encoding="utf-8",
    )

    (repo / "tests" / "test_sample.py").write_text(
        "def test_sample() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    return repo
