"""Read-only adapter for the local Git working tree.

Only read-only Git commands are ever executed. Command arguments are fixed
literals; any other command or flag raises ``CheckpointSafetyError``. Failures
degrade gracefully to empty values (matching the CSKS indexer pattern) so a
checkpoint can still be produced even when Git is unavailable or the directory
is not a repository.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

from careeros.exceptions import CheckpointSafetyError

from .models import LocalGitState

_READ_ONLY_INVOCATIONS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("git", "rev-parse", "HEAD"),
        ("git", "branch", "--show-current"),
        ("git", "log", "-1", "--format=%s"),
        ("git", "status", "--porcelain"),
        ("git", "rev-parse", "--abbrev-ref", "@{u}"),
        ("git", "show-ref", "refs/remotes/origin/main"),
        ("git", "remote", "get-url", "origin"),
    }
)


class _GitRun(NamedTuple):
    returncode: int | None
    stdout: str
    stderr: str


def _guard_argv(argv: list[str]) -> None:
    """Reject anything that is not a fixed, read-only git invocation."""
    if not isinstance(argv, list) or not argv or argv[0] != "git":
        raise CheckpointSafetyError("Git adapter may only run commands starting with 'git'.")
    if tuple(argv) not in _READ_ONLY_INVOCATIONS:
        raise CheckpointSafetyError(f"Refusing non-read-only git invocation: {' '.join(argv)}")


class LocalGitAdapter:
    """Collects read-only Git facts from a repository working tree."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def _run(self, *argv: str) -> _GitRun:
        full = ["git", *argv]
        _guard_argv(full)
        try:
            proc = subprocess.run(
                full,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            return _GitRun(proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip())
        except FileNotFoundError:
            return _GitRun(None, "", "git executable not found")
        except OSError as exc:
            return _GitRun(None, "", f"git unavailable: {exc}")

    def head_sha(self) -> str:
        result = self._run("rev-parse", "HEAD")
        return result.stdout if result.returncode == 0 else ""

    def current_branch(self) -> str:
        result = self._run("branch", "--show-current")
        return result.stdout if result.returncode == 0 else ""

    def recent_commit_subject(self) -> str:
        result = self._run("log", "-1", "--format=%s")
        return result.stdout if result.returncode == 0 else ""

    def working_tree_status(self) -> tuple[bool, int]:
        result = self._run("status", "--porcelain")
        if result.returncode != 0:
            return True, 0
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        return len(lines) == 0, len(lines)

    def upstream_ref(self) -> str:
        result = self._run("rev-parse", "--abbrev-ref", "@{u}")
        return result.stdout if result.returncode == 0 else ""

    def local_origin_main_ref(self) -> str:
        result = self._run("show-ref", "refs/remotes/origin/main")
        if result.returncode == 0 and result.stdout:
            return result.stdout.split()[0]
        return ""

    def remote_url(self, remote: str = "origin") -> str:
        result = self._run("remote", "get-url", remote)
        return result.stdout if result.returncode == 0 else ""

    def collect(self) -> LocalGitState:
        clean, dirty = self.working_tree_status()
        return LocalGitState(
            current_branch=self.current_branch(),
            local_head_sha=self.head_sha(),
            recent_commit_subject=self.recent_commit_subject(),
            working_tree_clean=clean,
            dirty_file_count=dirty,
            upstream_ref=self.upstream_ref(),
            local_origin_main_ref=self.local_origin_main_ref(),
        )