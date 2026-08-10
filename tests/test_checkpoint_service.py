"""Tests for the checkpoint service orchestration (end-to-end, hermetic)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from careeros.checkpoint.github import GitHubAccessError, GitHubProvider
from careeros.checkpoint.service import CheckpointService

DOC_TEMPLATE = (
    "## HEAD SHA\n\n- `{head}`\n\n"
    "## origin/main SHA\n\n- `{origin}`\n\n"
    "## Latest tag\n\n- `{tag}`\n\n"
    "## Open PRs\n\n- {prs}\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _head(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


class StaticGitHubProvider(GitHubProvider):
    name = "static"

    def __init__(
        self,
        *,
        main_sha: str = "",
        main_subject: str = "m",
        release: tuple[str, str] = ("", ""),
        prs: tuple[dict[str, str], ...] = (),
        raise_error: bool = False,
    ) -> None:
        self._main_sha = main_sha
        self._main_subject = main_subject
        self._release = release
        self._prs = prs
        self._raise_error = raise_error

    def repo_slug(self) -> str:
        return "owner/repo"

    def github_main_sha(self) -> str:
        if self._raise_error:
            raise GitHubAccessError("simulated failure")
        return self._main_sha

    def github_main_commit_subject(self) -> str:
        return self._main_subject

    def latest_release(self) -> tuple[str, str]:
        return self._release

    def open_pull_requests(self) -> tuple[dict[str, str], ...]:
        return self._prs


def _make_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    state_dir = repo / "docs" / "project-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "CURRENT_STATE.md").write_text(
        DOC_TEMPLATE.format(head="x" * 40, origin="x" * 40, tag="", prs="None."),
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial commit")
    head = _head(repo)
    _git(repo, "remote", "add", "origin", "https://github.com/raulgong66/career-OS.git")
    _git(repo, "update-ref", "refs/remotes/origin/main", head)
    return repo


def test_collect_reports_stale_origin_main(tmp_path: Path) -> None:
    "github main != github local origin ref -> 'github main' discrepancy."
    repo = _make_git_repo(tmp_path)
    provider = StaticGitHubProvider(main_sha="f" * 40, release=("v1.27.0", "8" * 40))
    checkpoint = CheckpointService(repo, github_provider=provider).collect()

    assert checkpoint.repository.remote_slug == "raulgong66/career-OS"
    assert checkpoint.repository.repo_name == "career-OS"
    assert checkpoint.remote.github_main_sha == "f" * 40
    assert checkpoint.sync.in_sync is False
    fields = {d.field for d in checkpoint.sync.discrepancies}
    assert "github main" in fields
    assert checkpoint.provenance["remote"] == "github"


def test_collect_in_sync_when_everything_matches(tmp_path: Path) -> None:
    "A clean tree with reconciled git/GitHub facts and no conflicting doc claims is 'in sync'."
    repo = _make_git_repo(tmp_path)
    # Remove the placeholder doc so it contributes no conflicting claims.
    _git(repo, "rm", "-q", "docs/project-state/CURRENT_STATE.md")
    _git(repo, "commit", "-q", "-m", "docs: drop placeholder state doc")
    head2 = _head(repo)
    _git(repo, "update-ref", "refs/remotes/origin/main", head2)

    provider = StaticGitHubProvider(main_sha=head2, release=("", ""), prs=())
    checkpoint = CheckpointService(repo, github_provider=provider).collect()
    assert checkpoint.sync.in_sync is True
    assert checkpoint.sync.discrepancies == ()
    assert checkpoint.project_docs.docs_found == ()


def test_collect_degrads_on_github_failure(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    service = CheckpointService(repo, github_provider=StaticGitHubProvider(raise_error=True))
    checkpoint = service.collect()
    assert checkpoint.remote.error != ""
    assert checkpoint.sync.in_sync is False
    assert any(d.field == "github" for d in checkpoint.sync.discrepancies)


def test_collect_skips_github_for_non_github_remote(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    _git(repo, "remote", "set-url", "origin", "https://example.com/x/y.git")
    checkpoint = CheckpointService(repo).collect()
    assert checkpoint.remote.error != ""
    assert checkpoint.repository.remote_slug == ""
    assert checkpoint.sync.in_sync is False


def test_generated_at_is_isoformat_and_tool_version_set(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    service = CheckpointService(repo, github_provider=StaticGitHubProvider(main_sha="f" * 40))
    checkpoint = service.collect()
    assert "T" in checkpoint.generated_at
    assert checkpoint.tool_version == "0.1.0"
    assert checkpoint.schema_version == "1.0.0"