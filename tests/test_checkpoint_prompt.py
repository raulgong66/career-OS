"""Tests for the New Chat bootstrap prompt renderer and its CLI wiring."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from careeros.checkpoint.cli import CHECKPOINT_APP
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
from careeros.checkpoint.render import render_json, render_markdown, render_prompt

runner = CliRunner()

GITHUB_MAIN = "f" * 40
LOCAL_HEAD = "a" * 40
LOCAL_ORIGIN_MAIN = "9" * 40


def make_checkpoint() -> RepositoryCheckpoint:
    return RepositoryCheckpoint(
        schema_version=SCHEMA_VERSION,
        tool_version="0.1.0",
        generated_at="2026-08-10T12:00:00+00:00",
        repository=RepositoryInfo(
            repo_name="career-OS",
            local_path="/tmp/repo",
            remote_url="https://github.com/raulgong66/career-OS.git",
            remote_slug="raulgong66/career-OS",
        ),
        local_git=LocalGitState(
            current_branch="docs/feature",
            local_head_sha=LOCAL_HEAD,
            recent_commit_subject="feat: add bootstrap prompt",
            working_tree_clean=True,
            dirty_file_count=0,
            upstream_ref="origin/docs/feature",
            local_origin_main_ref=LOCAL_ORIGIN_MAIN,
        ),
        remote=RemoteGitHubState(
            github_main_sha=GITHUB_MAIN,
            github_main_commit_subject="merge pr",
            latest_release_tag="v1.27.0",
            latest_release_sha="8" * 40,
            open_pr_count=1,
            open_prs=(
                {
                    "number": "14",
                    "title": "docs(governance): refresh project state after PR #13",
                    "head": "docs/project-state-refresh-pr13",
                    "base": "main",
                },
            ),
        ),
        project_docs=ProjectDocState(
            docs_found=("CURRENT_STATE.md",),
            documented_head_sha=GITHUB_MAIN,
            documented_origin_main_sha=GITHUB_MAIN,
            documented_latest_tag="v1.27.0",
            documented_open_pr_count="1",
            documented_test_status="Backend: 1125 passed",
            documented_authorized_action="Documentation-only: refresh CURRENT_STATE.md",
            documented_deferred_items=(
                "6e5281a roadmap preservation decision",
                "AGENTS.md stale test-count drift",
            ),
        ),
        sync=SyncState(
            in_sync=False,
            discrepancies=(
                Discrepancy(
                    field="github main",
                    source_a="github",
                    value_a=GITHUB_MAIN,
                    source_b="local origin/main",
                    value_b=LOCAL_ORIGIN_MAIN,
                    description="Local origin/main ref is stale relative to GitHub main.",
                ),
            ),
        ),
        provenance={"repository": "local_git", "remote": "github", "sync": "computed"},
    )


class FakeService:
    def __init__(self, *args, **kwargs) -> None:
        self.calls = 0

    def collect(self) -> RepositoryCheckpoint:
        self.calls += 1
        return make_checkpoint()


def test_prompt_contains_all_required_sections() -> None:
    text = render_prompt(make_checkpoint())
    for section in (
        "NEW CHAT — CAREEROS LIVE REPOSITORY CONTEXT",
        "IMPORTANT OPERATING RULES",
        "REPOSITORY",
        "CURRENT LOCAL STATE",
        "CURRENT GITHUB STATE",
        "PROJECT DOCUMENTATION STATE",
        "RECONCILIATION",
        "VERIFICATION / PROVENANCE",
        "CURRENT TASK",
        "END CHECKPOINT",
    ):
        assert section in text
    assert "[VERIFIED LIVE FACT]" in text
    assert "[DOCUMENTED FACT]" in text
    assert "[DISCREPANCY]" in text
    assert "Do not perform Git mutations unless explicitly authorized." in text
    assert "report the ambiguity rather than guessing" in text


def test_prompt_github_unavailable_reports_and_does_not_fabricate() -> None:
    cp = dataclasses.replace(
        make_checkpoint(),
        remote=RemoteGitHubState(error="GitHub state unavailable: simulated rate limit"),
    )
    text = render_prompt(cp)
    assert "[UNAVAILABLE SOURCE]" in text
    assert "GitHub state unavailable: simulated rate limit" in text
    assert "- Remote availability: unavailable" in text
    section = text.split("CURRENT GITHUB STATE")[1].split("PROJECT DOCUMENTATION STATE")[0]
    assert "- GitHub main:" not in section
    assert "- Latest release/tag:" not in section
    assert "- Open PRs:" not in section
    assert GITHUB_MAIN not in section
    assert "8" * 40 not in section


def test_prompt_reports_dirty_working_tree() -> None:
    cp = dataclasses.replace(
        make_checkpoint(),
        local_git=dataclasses.replace(
            make_checkpoint().local_git, working_tree_clean=False, dirty_file_count=5
        ),
    )
    text = render_prompt(cp)
    assert "- Working tree: dirty" in text
    assert "- Dirty files: 5" in text
    assert "- Working tree: clean" not in text


def test_prompt_preserves_all_discrepancies() -> None:
    discrepancies = (
        Discrepancy(
            field="github main",
            source_a="github",
            value_a=GITHUB_MAIN,
            source_b="local origin/main",
            value_b=LOCAL_ORIGIN_MAIN,
            description="Local origin/main ref is stale relative to GitHub main.",
        ),
        Discrepancy(
            field="HEAD",
            source_a="local_git",
            value_a=LOCAL_HEAD,
            source_b="CURRENT_STATE.md",
            value_b=GITHUB_MAIN,
            description="CURRENT_STATE.md HEAD SHA does not equal the local HEAD.",
        ),
    )
    cp = dataclasses.replace(
        make_checkpoint(),
        sync=SyncState(in_sync=False, discrepancies=discrepancies),
    )
    text = render_prompt(cp)
    assert "- In sync: no" in text
    assert "github main: github=f" in text
    assert "HEAD: local_git=a" in text
    assert "CURRENT_STATE.md HEAD SHA does not equal the local HEAD." in text
    assert "[DISCREPANCY]" in text


def test_prompt_distinguishes_documented_from_live() -> None:
    text = render_prompt(make_checkpoint())
    assert "CURRENT LOCAL STATE  [VERIFIED LIVE FACT]" in text
    assert "PROJECT DOCUMENTATION STATE  [DOCUMENTED FACT]" in text
    assert f"- HEAD: {LOCAL_HEAD}" in text
    assert f"- Documented HEAD: {GITHUB_MAIN}" in text
    assert f"- GitHub main: {GITHUB_MAIN}" in text
    assert f"- Documented origin/main: {GITHUB_MAIN}" in text


def test_prompt_preserves_open_pr_information() -> None:
    text = render_prompt(make_checkpoint())
    assert "- Open PRs: 1" in text
    assert "#14" in text
    assert "docs(governance): refresh project state after PR #13" in text
    assert "docs/project-state-refresh-pr13 -> main" in text


def test_prompt_preserves_deferred_items() -> None:
    text = render_prompt(make_checkpoint())
    assert "- Deferred/preservation items:" in text
    assert "6e5281a roadmap preservation decision" in text
    assert "AGENTS.md stale test-count drift" in text


def test_prompt_is_deterministic_except_generated_at() -> None:
    cp = make_checkpoint()
    first = render_prompt(cp)
    second = render_prompt(dataclasses.replace(cp, generated_at="2099-01-01T00:00:00+00:00"))
    assert first == second
    assert "generated_at" not in first
    with_ts = render_prompt(cp, include_generated_at=True)
    ts_line = "- generated_at: 2026-08-10T12:00:00+00:00"
    assert ts_line in with_ts
    first_lines = first.splitlines()
    expected = first_lines[:2] + [ts_line, ""] + first_lines[2:]
    assert with_ts.splitlines() == expected


def test_markdown_output_unchanged() -> None:
    text = render_markdown(make_checkpoint())
    assert text.startswith("# Live Repository Checkpoint")
    assert "- generated_at:" in text
    assert "## Local Git" in text
    assert "## Remote (GitHub)" in text
    assert "## Synchronization" in text
    assert "## Provenance" in text
    assert "DISCREPANCIES DETECTED" in text


def test_json_output_unchanged() -> None:
    payload = json.loads(render_json(make_checkpoint()))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["sync"]["in_sync"] is False
    assert payload["remote"]["open_pr_count"] == 1
    assert "prompt" not in payload


def test_cli_prompt_invokes_renderer(monkeypatch) -> None:
    service = FakeService()
    monkeypatch.setattr("careeros.checkpoint.cli.CheckpointService", lambda root, **kw: service)
    result = runner.invoke(CHECKPOINT_APP, ["--prompt"])
    assert result.exit_code == 0
    assert "NEW CHAT — CAREEROS LIVE REPOSITORY CONTEXT" in result.stdout
    assert "END CHECKPOINT" in result.stdout
    assert service.calls == 1


def test_cli_json_and_markdown_still_work(monkeypatch) -> None:
    monkeypatch.setattr("careeros.checkpoint.cli.CheckpointService", lambda root, **kw: FakeService())
    json_result = runner.invoke(CHECKPOINT_APP, ["--json"])
    assert json_result.exit_code == 0
    assert json.loads(json_result.stdout)["schema_version"] == SCHEMA_VERSION
    markdown_result = runner.invoke(CHECKPOINT_APP, [])
    assert markdown_result.exit_code == 0
    assert "# Live Repository Checkpoint" in markdown_result.stdout


def test_prompt_renderer_cannot_mutate_or_run_git(monkeypatch, tmp_path: Path) -> None:
    def _raise(*args, **kwargs):
        raise AssertionError("render_prompt must not run subprocess/git")

    monkeypatch.setattr(subprocess, "run", _raise)
    text = render_prompt(make_checkpoint())
    assert text
    assert list(tmp_path.iterdir()) == []
