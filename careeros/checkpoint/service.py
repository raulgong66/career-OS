"""Checkpoint service — orchestrates read-only collection and reconciliation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .conflicts import detect_discrepancies
from .github import GitHubAccessError, HttpGitHubProvider, parse_github_slug
from .local_git import LocalGitAdapter
from .models import (
    ProjectDocState,
    RemoteGitHubState,
    RepositoryCheckpoint,
    RepositoryInfo,
    SCHEMA_VERSION,
    SyncState,
)
from .project_state import ProjectStateReader

TOOL_VERSION = "0.1.0"


def _empty_remote(reason: str) -> RemoteGitHubState:
    return RemoteGitHubState(
        github_main_sha="",
        github_main_commit_subject="",
        latest_release_tag="",
        latest_release_sha="",
        open_pr_count=0,
        open_prs=(),
        error=reason,
    )


class CheckpointService:
    """Collects a read-only checkpoint and reconciles its sources of truth.

    The service never mutates the repository, Git working tree, GitHub state, or
    project-state documentation. GitHub access failures degrade to an
    ``error`` fact on the remote block (and a discrepancy) rather than crashing.
    """

    def __init__(
        self,
        repo_root: Path,
        *,
        local_git: LocalGitAdapter | None = None,
        github_provider=None,
        doc_reader: ProjectStateReader | None = None,
        tool_version: str = TOOL_VERSION,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.local_git = local_git or LocalGitAdapter(self.repo_root)
        self._github_provider = github_provider
        self.doc_reader = doc_reader or ProjectStateReader(self.repo_root)
        self.tool_version = tool_version

    def _remote_state(self) -> RemoteGitHubState:
        provider = self._github_provider
        if provider is None:
            slug = parse_github_slug(self.local_git.remote_url())
            if not slug:
                return _empty_remote(
                    "GitHub state unavailable: remote URL is not a github.com repository."
                )
            provider = HttpGitHubProvider(slug)

        try:
            prs = provider.open_pull_requests()
            release_tag, release_sha = provider.latest_release()
            return RemoteGitHubState(
                github_main_sha=provider.github_main_sha(),
                github_main_commit_subject=provider.github_main_commit_subject(),
                latest_release_tag=release_tag,
                latest_release_sha=release_sha,
                open_pr_count=len(prs),
                open_prs=prs,
                error="",
            )
        except GitHubAccessError as exc:
            return _empty_remote(f"GitHub state unavailable: {exc}")

    def collect(self) -> RepositoryCheckpoint:
        local = self.local_git.collect()
        remote = self._remote_state()
        doc = self.doc_reader.read_current_state()

        discrepancies = detect_discrepancies(local, remote, doc)
        sync = SyncState(in_sync=len(discrepancies) == 0, discrepancies=discrepancies)

        slug = parse_github_slug(self.local_git.remote_url())
        slug_repo = slug.split("/", 1)[1] if "/" in slug else ""
        repo_info = RepositoryInfo(
            repo_name=slug_repo or self.repo_root.name,
            local_path=str(self.repo_root.resolve()),
            remote_url=self.local_git.remote_url(),
            remote_slug=slug,
        )

        provenance = {
            "repository": "local_git",
            "local_git": "local_git",
            "remote": "github" if remote.github_main_sha else "unavailable",
            "project_docs": "doc",
            "sync": "computed",
        }

        return RepositoryCheckpoint(
            schema_version=SCHEMA_VERSION,
            tool_version=self.tool_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            repository=repo_info,
            local_git=local,
            remote=remote,
            project_docs=doc,
            sync=sync,
            provenance=provenance,
        )