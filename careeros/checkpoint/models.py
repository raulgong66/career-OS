"""Canonical checkpoint model for the Live Repository Checkpoint capability.

The model is intentionally read-only and immutable. Every fact records where it
came from (``source``) so a checkpoint can always distinguish authoritative
remote state from potentially stale local state, and report conflicts rather
than silently resolving them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class Discrepancy:
    """A detected conflict between two sources for the same fact."""

    field: str
    source_a: str
    value_a: str
    source_b: str
    value_b: str
    description: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "source_a": self.source_a,
            "value_a": self.value_a,
            "source_b": self.source_b,
            "value_b": self.value_b,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Discrepancy":
        return cls(
            field=str(data.get("field", "")),
            source_a=str(data.get("source_a", "")),
            value_a=str(data.get("value_a", "")),
            source_b=str(data.get("source_b", "")),
            value_b=str(data.get("value_b", "")),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class RepositoryInfo:
    """Identity facts about the repository."""

    repo_name: str
    local_path: str
    remote_url: str = ""
    remote_slug: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "repo_name": self.repo_name,
            "local_path": self.local_path,
            "remote_url": self.remote_url,
            "remote_slug": self.remote_slug,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryInfo":
        return cls(
            repo_name=str(data.get("repo_name", "")),
            local_path=str(data.get("local_path", "")),
            remote_url=str(data.get("remote_url", "")),
            remote_slug=str(data.get("remote_slug", "")),
        )


@dataclass(frozen=True)
class LocalGitState:
    """Read-only snapshot of the local Git working tree."""

    current_branch: str = ""
    local_head_sha: str = ""
    recent_commit_subject: str = ""
    working_tree_clean: bool = True
    dirty_file_count: int = 0
    upstream_ref: str = ""
    local_origin_main_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_branch": self.current_branch,
            "local_head_sha": self.local_head_sha,
            "recent_commit_subject": self.recent_commit_subject,
            "working_tree_clean": self.working_tree_clean,
            "dirty_file_count": self.dirty_file_count,
            "upstream_ref": self.upstream_ref,
            "local_origin_main_ref": self.local_origin_main_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalGitState":
        return cls(
            current_branch=str(data.get("current_branch", "")),
            local_head_sha=str(data.get("local_head_sha", "")),
            recent_commit_subject=str(data.get("recent_commit_subject", "")),
            working_tree_clean=bool(data.get("working_tree_clean", True)),
            dirty_file_count=int(data.get("dirty_file_count", 0)),
            upstream_ref=str(data.get("upstream_ref", "")),
            local_origin_main_ref=str(data.get("local_origin_main_ref", "")),
        )


@dataclass(frozen=True)
class RemoteGitHubState:
    """Authoritative GitHub state (read-only, HTTP GET only)."""

    github_main_sha: str = ""
    github_main_commit_subject: str = ""
    latest_release_tag: str = ""
    latest_release_sha: str = ""
    open_pr_count: int = 0
    open_prs: tuple[dict[str, str], ...] = ()
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "github_main_sha": self.github_main_sha,
            "github_main_commit_subject": self.github_main_commit_subject,
            "latest_release_tag": self.latest_release_tag,
            "latest_release_sha": self.latest_release_sha,
            "open_pr_count": self.open_pr_count,
            "open_prs": [dict(pr) for pr in self.open_prs],
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemoteGitHubState":
        return cls(
            github_main_sha=str(data.get("github_main_sha", "")),
            github_main_commit_subject=str(data.get("github_main_commit_subject", "")),
            latest_release_tag=str(data.get("latest_release_tag", "")),
            latest_release_sha=str(data.get("latest_release_sha", "")),
            open_pr_count=int(data.get("open_pr_count", 0)),
            open_prs=tuple(dict(pr) for pr in data.get("open_prs", [])),
            error=str(data.get("error", "")),
        )


@dataclass(frozen=True)
class ProjectDocState:
    """Facts parsed from ``docs/project-state/*.md`` (a secondary source)."""

    docs_found: tuple[str, ...] = ()
    documented_head_sha: str = ""
    documented_origin_main_sha: str = ""
    documented_latest_tag: str = ""
    documented_open_pr_count: str = ""
    documented_test_status: str = ""
    documented_authorized_action: str = ""
    documented_deferred_items: tuple[str, ...] = ()
    documented_last_checkpoint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "docs_found": list(self.docs_found),
            "documented_head_sha": self.documented_head_sha,
            "documented_origin_main_sha": self.documented_origin_main_sha,
            "documented_latest_tag": self.documented_latest_tag,
            "documented_open_pr_count": self.documented_open_pr_count,
            "documented_test_status": self.documented_test_status,
            "documented_authorized_action": self.documented_authorized_action,
            "documented_deferred_items": list(self.documented_deferred_items),
            "documented_last_checkpoint": self.documented_last_checkpoint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectDocState":
        return cls(
            docs_found=tuple(str(x) for x in data.get("docs_found", [])),
            documented_head_sha=str(data.get("documented_head_sha", "")),
            documented_origin_main_sha=str(data.get("documented_origin_main_sha", "")),
            documented_latest_tag=str(data.get("documented_latest_tag", "")),
            documented_open_pr_count=str(data.get("documented_open_pr_count", "")),
            documented_test_status=str(data.get("documented_test_status", "")),
            documented_authorized_action=str(data.get("documented_authorized_action", "")),
            documented_deferred_items=tuple(str(x) for x in data.get("documented_deferred_items", [])),
            documented_last_checkpoint=str(data.get("documented_last_checkpoint", "")),
        )


@dataclass(frozen=True)
class SyncState:
    """Synchronization status across authoritative and secondary sources."""

    in_sync: bool
    discrepancies: tuple[Discrepancy, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_sync": self.in_sync,
            "discrepancies": [d.to_dict() for d in self.discrepancies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        return cls(
            in_sync=bool(data.get("in_sync", False)),
            discrepancies=tuple(Discrepancy.from_dict(d) for d in data.get("discrepancies", [])),
        )


@dataclass(frozen=True)
class RepositoryCheckpoint:
    """A complete read-only Live Repository Checkpoint."""

    schema_version: str
    tool_version: str
    generated_at: str
    repository: RepositoryInfo
    local_git: LocalGitState
    remote: RemoteGitHubState
    project_docs: ProjectDocState
    sync: SyncState
    provenance: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_version": self.tool_version,
            "generated_at": self.generated_at,
            "repository": self.repository.to_dict(),
            "local_git": self.local_git.to_dict(),
            "remote": self.remote.to_dict(),
            "project_docs": self.project_docs.to_dict(),
            "sync": self.sync.to_dict(),
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryCheckpoint":
        return cls(
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            tool_version=str(data.get("tool_version", "")),
            generated_at=str(data.get("generated_at", "")),
            repository=RepositoryInfo.from_dict(data.get("repository", {})),
            local_git=LocalGitState.from_dict(data.get("local_git", {})),
            remote=RemoteGitHubState.from_dict(data.get("remote", {})),
            project_docs=ProjectDocState.from_dict(data.get("project_docs", {})),
            sync=SyncState.from_dict(data.get("sync", {})),
            provenance=dict(data.get("provenance", {})),
        )