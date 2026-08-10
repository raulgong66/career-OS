"""Tests for the canonical checkpoint model."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

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
            local_head_sha="a" * 40,
            recent_commit_subject="feat: something",
            working_tree_clean=True,
            dirty_file_count=0,
            upstream_ref="origin/main",
            local_origin_main_ref="b" * 40,
        ),
        remote=RemoteGitHubState(
            github_main_sha="c" * 40,
            github_main_commit_subject="merge pr",
            latest_release_tag="v1.27.0",
            latest_release_sha="d" * 40,
            open_pr_count=1,
            open_prs=({"number": "1", "title": "x", "head": "h", "base": "main"},),
        ),
        project_docs=ProjectDocState(
            docs_found=("CURRENT_STATE.md",),
            documented_head_sha="e" * 40,
        ),
        sync=SyncState(in_sync=False, discrepancies=(Discrepancy("f", "a", "1", "b", "2"),)),
        provenance={"remote": "github", "local_git": "local_git"},
    )


def test_to_dict_json_serializable() -> None:
    data = make_checkpoint().to_dict()
    json.dumps(data)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["remote"]["open_prs"] == [{"number": "1", "title": "x", "head": "h", "base": "main"}]


def test_from_dict_round_trip() -> None:
    original = make_checkpoint()
    restored = RepositoryCheckpoint.from_dict(original.to_dict())
    assert restored == original


def test_model_is_immutable() -> None:
    checkpoint = make_checkpoint()
    with pytest.raises(FrozenInstanceError):
        checkpoint.tool_version = "other"


def test_discrepancy_round_trip() -> None:
    d = Discrepancy(field="github main", source_a="github", value_a="1", source_b="local", value_b="2")
    assert Discrepancy.from_dict(d.to_dict()) == d


def test_empty_states_round_trip() -> None:
    checkpoint = RepositoryCheckpoint(
        schema_version=SCHEMA_VERSION,
        tool_version="0.1.0",
        generated_at="t",
        repository=RepositoryInfo(repo_name="x", local_path="/x"),
        local_git=LocalGitState(),
        remote=RemoteGitHubState(),
        project_docs=ProjectDocState(),
        sync=SyncState(in_sync=True),
        provenance={},
    )
    assert RepositoryCheckpoint.from_dict(checkpoint.to_dict()) == checkpoint