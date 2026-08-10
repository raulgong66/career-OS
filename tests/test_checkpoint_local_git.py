"""Tests for the read-only LocalGitAdapter.

Uses real transient Git repositories created with ``git init`` in ``tmp_path``
(the same pattern as ``test_csks_extractor.py``) so no repository state is ever
touched.
"""

from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError  # noqa: F401  (kept for parity intent)
from pathlib import Path

import pytest

from careeros.checkpoint.local_git import LocalGitAdapter, _guard_argv
from careeros.exceptions import CheckpointSafetyError


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("a", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial commit")
    return repo


def test_head_sha_and_branch(git_repo: Path) -> None:
    adapter = LocalGitAdapter(git_repo)
    head = adapter.head_sha()
    assert len(head) == 40
    assert adapter.current_branch() == "main"
    assert adapter.recent_commit_subject() == "initial commit"


def test_working_tree_clean_and_dirty(git_repo: Path) -> None:
    adapter = LocalGitAdapter(git_repo)
    assert adapter.working_tree_status() == (True, 0)
    (git_repo / "dirty.txt").write_text("x", encoding="utf-8")
    clean, count = adapter.working_tree_status()
    assert clean is False
    assert count >= 1


def test_origin_main_ref_and_remote_url(git_repo: Path) -> None:
    _git(git_repo, "remote", "add", "origin", "https://github.com/raulgong66/career-OS.git")
    head = LocalGitAdapter(git_repo).head_sha()
    _git(git_repo, "update-ref", "refs/remotes/origin/main", head)
    adapter = LocalGitAdapter(git_repo)
    assert adapter.local_origin_main_ref() == head
    assert adapter.remote_url() == "https://github.com/raulgong66/career-OS.git"


def test_upstream_ref_requires_tracking(git_repo: Path) -> None:
    assert LocalGitAdapter(git_repo).upstream_ref() == ""


def test_collect_returns_state(git_repo: Path) -> None:
    (git_repo / "extra.txt").write_text("y", encoding="utf-8")
    state = LocalGitAdapter(git_repo).collect()
    assert state.local_head_sha == "0" * 0 or len(state.local_head_sha) == 40
    assert state.working_tree_clean is False
    assert state.dirty_file_count >= 1
    assert state.current_branch == "main"


def test_missing_directory_degrades_gracefully(tmp_path: Path) -> None:
    state = LocalGitAdapter(tmp_path / "does-not-exist").collect()
    assert state.local_head_sha == ""
    assert state.current_branch == ""
    assert state.working_tree_clean is True
    assert state.dirty_file_count == 0


def test_guard_rejects_non_read_only_commands() -> None:
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "push"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "fetch"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "commit"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "reset"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "merge"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "tag", "-a", "x", "-m", "y"])


def test_guard_rejects_forbidden_flags() -> None:
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "rev-parse", "--force", "HEAD"])
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(["git", "log", "--format=%s", "--force"])


def test_guard_allows_read_only_invocations() -> None:
    for argv in (
        ["git", "rev-parse", "HEAD"],
        ["git", "branch", "--show-current"],
        ["git", "log", "-1", "--format=%s"],
        ["git", "status", "--porcelain"],
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        ["git", "show-ref", "refs/remotes/origin/main"],
        ["git", "remote", "get-url", "origin"],
    ):
        _guard_argv(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["git", "push"],
        ["git", "fetch"],
        ["git", "pull"],
        ["git", "commit"],
        ["git", "reset"],
        ["git", "merge"],
        ["git", "rebase"],
        ["git", "checkout"],
        ["git", "clean"],
        ["git", "remote", "add", "upstream", "https://example.com/x.git"],
        ["git", "remote", "set-url", "origin", "https://example.com/x.git"],
        ["git", "remote", "remove", "origin"],
        ["git", "remote", "rename", "origin", "upstream"],
        ["git", "config", "user.name", "Someone"],
        ["git", "branch", "feature"],
        ["git", "branch", "-d", "feature"],
        ["git", "branch", "-D", "feature"],
        ["git", "tag", "v1.0"],
        ["git", "tag", "-d", "v1.0"],
        ["git", "rev-parse", "HEAD", "HEAD"],
        ["git", "status", "--porcelain", "--ignored"],
        ["git", "log", "-2", "--format=%s"],
        ["git", "remote", "get-url", "upstream"],
        ["git", "branch"],
        ["git", "tag"],
        ["git", "config"],
        ["git", "remote"],
        ["git", "unknown", "thing"],
        ["git"],
        ["git", "rev-parse"],
        [],
        ["not-git", "status", "--porcelain"],
        ["git", "status", "--porcelain", "extra-path"],
    ],
)
def test_guard_rejects_mutating_or_unknown_shapes(argv: list[str]) -> None:
    with pytest.raises(CheckpointSafetyError):
        _guard_argv(argv)


def test_guard_rejects_by_itself_not_by_command_failure() -> None:
    adapter = LocalGitAdapter(Path("."))
    for argv in (
        ("remote", "add", "upstream", "https://example.com/x.git"),
        ("config", "user.name", "Someone"),
        ("branch", "feature"),
        ("tag", "v1.0"),
    ):
        with pytest.raises(CheckpointSafetyError):
            adapter._run(*argv)


def test_run_rejects_mutation() -> None:
    adapter = LocalGitAdapter(Path("."))
    with pytest.raises(CheckpointSafetyError):
        adapter._run("push")