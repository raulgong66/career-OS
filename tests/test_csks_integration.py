"""Integration tests for the CSKS foundation (M1.22).

Covers the full pipeline (index -> query -> format), the CLI sub-app, the REST
router, and the architectural constraint that CSKS reuses the existing
`careeros.knowledge.KnowledgeGraph`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from careeros.csks.api import build_csks_router
from careeros.csks.cli import CSKS_APP
from careeros.csks.indexer import CSKSIndexer


@pytest.fixture
def indexer(csks_sample_repo: Path) -> CSKSIndexer:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()
    return indexer


def test_full_pipeline_index_to_query(indexer: CSKSIndexer) -> None:
    assert indexer.graph is not None
    assert indexer.graph.node_count > 0

    engine = indexer.get_query_engine()
    result = engine.query("List all domains")
    assert result.query_type == "type_filter"
    assert result.entities_found >= 3
    assert result.confidence == 1.0


def test_indexer_status(indexer: CSKSIndexer) -> None:
    status = indexer.get_status()
    assert status["status"] == "ready"
    assert status["entity_count"] == indexer.graph.node_count
    assert status["relationship_count"] == indexer.graph.edge_count
    assert status["indexed_files"] >= 1
    assert status["git_commit"] == ""
    assert status["last_build_ms"] >= 0


def test_indexer_persists_metadata(indexer: CSKSIndexer) -> None:
    metadata_path = indexer._metadata_path
    assert metadata_path.exists()
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["version"] == "1.0"
    assert payload["entity_count"] == indexer.graph.node_count


def test_indexer_get_entity(indexer: CSKSIndexer) -> None:
    details = indexer.get_entity("component.careeros.profile_loader.ProfileLoader")
    assert details is not None
    assert details["type"] == "component"
    assert details["label"] == "ProfileLoader"
    assert details["incoming_relationships"] or details["outgoing_relationships"]


def test_indexer_get_entity_missing(indexer: CSKSIndexer) -> None:
    assert indexer.get_entity("component.nope.Missing") is None


def test_indexer_search_by_type(indexer: CSKSIndexer) -> None:
    results = indexer.search(entity_type="domain", limit=100)
    assert len(results) >= 3
    assert all(r["type"] == "domain" for r in results)


def test_indexer_incremental_update_stub(indexer: CSKSIndexer) -> None:
    before = indexer.graph.node_count
    graph = indexer.incremental_update([])
    assert graph.node_count == before


def test_cli_query_end_to_end(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["query", "List all domains", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "Found" in result.output
    assert "domain.profile_management" in result.output


def test_cli_default_repo_root_is_repo_root() -> None:
    from careeros.csks.cli import _default_repo_root

    root = _default_repo_root()
    assert (root / "careeros" / "csks" / "cli.py").is_file()
    assert (root / "careeros" / "csks").is_dir()


def test_cli_query_without_repo_root(
    monkeypatch: pytest.MonkeyPatch, csks_sample_repo: Path
) -> None:
    from careeros.csks import cli

    monkeypatch.setattr(cli, "_default_repo_root", lambda: csks_sample_repo)
    runner = CliRunner()

    for question, expected in [
        ("List domains", "domain.profile_management"),
        ("List API endpoints", "api.get.profiles"),
        ("What is ADR-008?", "adr.008"),
    ]:
        result = runner.invoke(CSKS_APP, ["query", question])
        assert result.exit_code == 0, result.output
        assert expected in result.output


def test_cli_query_json_output(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["query", "M1.21 status", "--repo-root", str(csks_sample_repo), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["query_type"] == "status_check"
    assert payload["answer"]


def test_cli_entity_command(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["entity", "rule.total_years_experience", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "rule.total_years_experience" in result.output


def test_cli_search_command(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["search", "--type", "domain", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "domain.profile_management" in result.output


def test_cli_index_command(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["index", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "Index built" in result.output
    assert "nodes" in result.output


def test_cli_status_command(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["status", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 0, result.output
    assert "Entity Count" in result.output
    assert "Status" in result.output


def test_cli_entity_not_found_exits_nonzero(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        ["entity", "component.nope.Missing", "--repo-root", str(csks_sample_repo)],
    )
    assert result.exit_code == 1
    assert "not found" in result.output


def _write_profile(path: Path, *, person_id: str, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    repeated = "Familiar with the Agile way of working and DevOps concepts."
    path.write_text(
        (
            f"profileVersion: 1.0.0\n"
            f"person:\n"
            f"  id: {person_id}\n"
            f"  names:\n"
            f"  - value: {name}\n"
            f"    usage: professional\n"
            f"professionalSummaries:\n"
            f"- id: sum-1\n"
            f"  text: {repeated}\n"
            f"experiences:\n"
            f"- id: exp-1\n"
            f"  title: Engineer\n"
            f"  scope: {repeated}\n"
            f"achievements: []\n"
            f"projects: []\n"
            f"skills: []\n"
            f"certifications: []\n"
            f"education: []\n"
        ),
        encoding="utf-8",
    )
    return path


def test_cli_query_profile_id_resolution(tmp_path: Path) -> None:
    """csks query --profile resolves a profile id through the repository."""
    profile = _write_profile(
        tmp_path / "profiles" / "staging" / "person-hechavarria-profile.yaml",
        person_id="person-hechavarria",
        name="Rene Hechavarria",
    )
    assert profile.is_file()

    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        [
            "query",
            "Show duplicate narrative",
            "--profile",
            "person-hechavarria",
            "--repo-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "person-hechavarria" in result.output
    assert "duplicate narrative group" in result.output


def test_cli_query_profile_path_backward_compatible(tmp_path: Path) -> None:
    """csks query --profile keeps explicit filesystem paths working."""
    profile = _write_profile(
        tmp_path / "profiles" / "raul-gongora-profile.yaml",
        person_id="person-raul-gongora",
        name="Raul Gongora",
    )

    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        [
            "query",
            "Show duplicate narrative",
            "--profile",
            str(profile),
            "--repo-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "person-raul-gongora" in result.output


def test_cli_query_profile_unknown_id_exits_nonzero(tmp_path: Path) -> None:
    """csks query --profile with an unresolvable id exits with a friendly error."""
    runner = CliRunner()
    result = runner.invoke(
        CSKS_APP,
        [
            "query",
            "Show duplicate narrative",
            "--profile",
            "person-does-not-exist",
            "--repo-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Profile not found" in result.output


def test_api_router_end_to_end(indexer: CSKSIndexer, csks_sample_repo: Path) -> None:
    fastapi = pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(build_csks_router(indexer))

    client = TestClient(app)

    status = client.get("/csks/status")
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert status.json()["entity_count"] == indexer.graph.node_count

    response = client.get("/csks/query", params={"q": "What is ProfileLoader?"})
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] == "entity_lookup"
    assert "ProfileLoader" in body["answer"]
    assert body["citations"]
    assert body["confidence"] == 1.0

    entity = client.get("/csks/entity/component.careeros.profile_loader.ProfileLoader")
    assert entity.status_code == 200
    assert entity.json()["type"] == "component"

    missing = client.get("/csks/entity/component.nope.Missing")
    assert missing.status_code == 404

    search = client.get("/csks/search", params={"type": "domain"})
    assert search.status_code == 200
    assert search.json()["count"] >= 3


def test_csks_router_wired_into_main_app() -> None:
    from api.main import app
    from careeros.csks.api import CSKS_ROUTER

    included = [
        route for route in app.routes
        if type(route).__name__ == "_IncludedRouter"
    ]
    assert included
    assert any(
        getattr(route, "original_router", None) is CSKS_ROUTER
        for route in included
    )


def test_csks_app_wired_into_main_cli() -> None:
    from careeros.csks.cli import CSKS_APP
    from careeros_cli.main import app

    assert any(getattr(g, "typer_instance", None) is CSKS_APP for g in app.registered_groups)


def test_no_parallel_knowledge_graph_implementation() -> None:
    """Acceptance criterion: CSKS reuses careeros.knowledge.KnowledgeGraph."""
    import careeros.csks as csks_package

    for path in Path(csks_package.__file__).parent.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "class KnowledgeGraph" not in source, f"Parallel graph in {path.name}"
