"""Live Repository Checkpoint capability.

Provides a deterministic, read-only snapshot of the repository: authoritative
GitHub state, local Git state, the project-state documentation, and the
conflicts between them. The capability never mutates the repository, Git
working tree, GitHub state, or project-state documentation.
"""

from __future__ import annotations

from .conflicts import compute_sync_state, detect_discrepancies
from .github import (
    GitHubAccessError,
    GitHubProvider,
    HttpGitHubProvider,
    create_github_provider,
    parse_github_slug,
)
from .local_git import LocalGitAdapter
from .models import (
    Discrepancy,
    LocalGitState,
    ProjectDocState,
    RemoteGitHubState,
    RepositoryCheckpoint,
    RepositoryInfo,
    SCHEMA_VERSION,
    SyncState,
)
from .project_state import ProjectStateReader
from .render import render_json, render_markdown, render_prompt
from .service import CheckpointService, TOOL_VERSION

__all__ = [
    "CheckpointService",
    "TOOL_VERSION",
    "SCHEMA_VERSION",
    "RepositoryCheckpoint",
    "RepositoryInfo",
    "LocalGitState",
    "RemoteGitHubState",
    "ProjectDocState",
    "SyncState",
    "Discrepancy",
    "detect_discrepancies",
    "compute_sync_state",
    "LocalGitAdapter",
    "GitHubProvider",
    "HttpGitHubProvider",
    "GitHubAccessError",
    "create_github_provider",
    "parse_github_slug",
    "ProjectStateReader",
    "render_json",
    "render_markdown",
    "render_prompt",
]