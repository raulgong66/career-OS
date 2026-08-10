"""Tests for the checkpoint renderers and the CLI sub-application."""

from __future__ import annotations

import dataclasses
import json

from typer.testing import CliRunner

from careeros.checkpoint.cli import CHECKPOINT_APP, _default_repo_root
from careeros.checkpoint.models import (
    SCHEMA_VERSION,
    Discrepancy,
    LocalGitState,
    ProjectDocState,
    RemoteGitHubState,
    RepositoryCheckpoint,
    RepositoryInfo,
    SyncState,
)
from careeros.checkpoint.render import render_json, render_markdown

runner = CliRunner()

GITHUB_MAIN = "f" * 40
LOCAL_HEAD = "a" * 40


def make_checkpoint() -> RepositoryCheckpoint:
    return RepositoryCheckpoint(
        schema_version=SCHEMA_VERSION,
        tool_version="0.1.0",
        generated_at="2026-08-09T00:00:00+00:00",
        repository=RepositoryInfo(
            repo_name="career-OS",
            local_path="/tmp/repo",
            remote_url="https://github.com/raulgong66/career-OS.git",
            remote_slug="raulgong66/career-OS",
        ),
        local_git=LocalGitState(
            current_branch="main",
            local_head_sha=LOCAL_HEAD,
            recent_commit_subject="feat: x",
            working_tree_clean=True,
            dirty_file_count=0,
            upstream_ref="origin/main",
            local_origin_main_ref="9" * 40,
        ),
        remote=RemoteGitHubState(
            github_main_sha=GITHUB_MAIN,
            github_main_commit_subject="merge pr",
            latest_release_tag="v1.27.0",
            latest_release_sha="8" * 40,
            open_pr_count=0,
            open_prs=(),
        ),
        project_docs=ProjectDocState(
            docs_found=("CURRENT_STATE.md",),
            documented_head_sha=LOCAL_HEAD,
            documented_origin_main_sha=GITHUB_MAIN,
            documented_latest_tag="v1.27.0",
            documented_open_pr_count="None.",
            documented_test_status="1041 passed",
        ),
        sync=SyncState(
            in_sync=False,
            discrepancies=(
                Discrepancy(
                    field="github main",
                    source_a="github",
                    value_a=GITHUB_MAIN,
                    source_b="local origin/main",
                    value_b="9" * 40,
                    description="Local origin/main ref is stale relative to GitHub main.",
                ),
            ),
        ),
        provenance={"remote": "github", "local_git": "local_git"},
    )


class FakeService:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def collect(self) -> RepositoryCheckpoint:
        return make_checkpoint()


def test_render_markdown_contains_sections() -> None:
    text = render_markdown(make_checkpoint())
    assert "# Live Repository Checkpoint" in text
    assert "## Local Git" in text
    assert "## Remote (GitHub)" in text
    assert "## Synchronization" in text
    assert "DISCREPANCIES DETECTED" in text
    assert "github main" in text
    assert "## Provenance" in text


def test_render_markdown_in_sync() -> None:
    cp = dataclasses.replace(make_checkpoint(), sync=SyncState(in_sync=True, discrepancies=()))
    assert "IN SYNC" in render_markdown(cp)


def test_render_json_is_valid() -> None:
    payload = json.loads(render_json(make_checkpoint()))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["sync"]["in_sync"] is False


def test_cli_live_markdown(monkeypatch) -> None:
    monkeypatch.setattr("careeros.checkpoint.cli.CheckpointService", FakeService)
    result = runner.invoke(CHECKPOINT_APP, [])
    assert result.exit_code == 0
    assert "# Live Repository Checkpoint" in result.stdout


def test_cli_live_json(monkeypatch) -> None:
    monkeypatch.setattr("careeros.checkpoint.cli.CheckpointService", FakeService)
    result = runner.invoke(CHECKPOINT_APP, ["--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["sync"]["discrepancies"][0]["field"] == "github main"


def test_default_repo_root_is_repository() -> None:
    assert (_default_repo_root() / "AGENTS.md").exists()


def test_checkpoint_app_wired_into_main_cli() -> None:
    from careeros_cli.main import app

    assert any(getattr(g, "typer_instance", None) is CHECKPOINT_APP for g in app.registered_groups)