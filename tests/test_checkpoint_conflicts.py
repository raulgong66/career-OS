"""Tests for the pure source-of-truth / conflict detection logic."""

from __future__ import annotations

from careeros.checkpoint.conflicts import compute_sync_state, detect_discrepancies
from careeros.checkpoint.models import (
    LocalGitState,
    ProjectDocState,
    RemoteGitHubState,
)

gh = "f" * 40
loc = "a" * 40
doc = "b" * 40


def _state(
    *,
    local_head: str = loc,
    origin_ref: str = gh,
    clean: bool = True,
    dirty: int = 0,
    github_main: str = gh,
    doc_origin: str = gh,
    doc_head: str = loc,
    doc_tag: str = "v1.27.0",
    github_tag: str = "v1.27.0",
    doc_prs: str = "None.",
    github_prs: int = 0,
    remote_error: str = "",
) -> tuple[LocalGitState, RemoteGitHubState, ProjectDocState]:
    local = LocalGitState(
        current_branch="main",
        local_head_sha=local_head,
        working_tree_clean=clean,
        dirty_file_count=dirty,
        local_origin_main_ref=origin_ref,
    )
    remote = RemoteGitHubState(
        github_main_sha=github_main,
        latest_release_tag=github_tag,
        open_pr_count=github_prs,
        error=remote_error,
    )
    doc_state = ProjectDocState(
        documented_head_sha=doc_head,
        documented_origin_main_sha=doc_origin,
        documented_latest_tag=doc_tag,
        documented_open_pr_count=doc_prs,
    )
    return local, remote, doc_state


def test_no_conflicts_when_consistent() -> None:
    local, remote, doc_state = _state()
    assert detect_discrepancies(local, remote, doc_state) == ()
    assert compute_sync_state(local, remote, doc_state).in_sync is True


def test_stale_local_origin_main_ref_reported() -> None:
    local, remote, doc_state = _state(origin_ref="9" * 40)
    discrepancies = detect_discrepancies(local, remote, doc_state)
    assert any(d.field == "github main" for d in discrepancies)
    assert compute_sync_state(local, remote, doc_state).in_sync is False


def test_stale_documented_origin_main_reported() -> None:
    local, remote, doc_state = _state(doc_origin="9" * 40)
    assert any(d.field == "origin/main" for d in detect_discrepancies(local, remote, doc_state))


def test_documented_head_mismatch_reported() -> None:
    local, remote, doc_state = _state(doc_head="9" * 40)
    assert any(d.field == "HEAD" for d in detect_discrepancies(local, remote, doc_state))


def test_tag_mismatch_reported() -> None:
    local, remote, doc_state = _state(doc_tag="v1.26.0", github_tag="v1.27.0")
    assert any(d.field == "latest tag" for d in detect_discrepancies(local, remote, doc_state))


def test_dirty_working_tree_reported() -> None:
    local, remote, doc_state = _state(clean=False, dirty=3)
    discrepancies = detect_discrepancies(local, remote, doc_state)
    assert any(d.field == "working tree" for d in discrepancies)


def test_github_unavailable_reported() -> None:
    local, remote, doc_state = _state(remote_error="boom", github_main="")
    discrepancies = detect_discrepancies(local, remote, doc_state)
    assert any(d.field == "github" for d in discrepancies)


def test_open_pr_count_mismatch_reported() -> None:
    local, remote, doc_state = _state(doc_prs="None.", github_prs=2)
    assert any(d.field == "open PRs" for d in detect_discrepancies(local, remote, doc_state))


def test_open_pr_mismatch_with_github_error_not_duplicated() -> None:
    local, remote, doc_state = _state(doc_prs="None.", github_prs=0, remote_error="boom", github_main="")
    fields = [d.field for d in detect_discrepancies(local, remote, doc_state)]
    assert fields.count("github") == 1
    assert "open PRs" not in fields


def test_multiple_conflicts_all_reported() -> None:
    local, remote, doc_state = _state(
        origin_ref="1" * 40,
        doc_head="2" * 40,
        doc_tag="v1.26.0",
        github_tag="v1.27.0",
        clean=False,
        dirty=1,
    )
    fields = {d.field for d in detect_discrepancies(local, remote, doc_state)}
    assert {
        "github main",
        "HEAD",
        "latest tag",
        "working tree",
    } <= fields
    assert compute_sync_state(local, remote, doc_state).in_sync is False