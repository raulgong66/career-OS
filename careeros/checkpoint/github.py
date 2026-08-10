"""Read-only GitHub provider.

No GitHub access existed in the repository before this capability. This module
follows the ``careeros.ai`` adapter pattern: an abstract capability interface,
an HTTP implementation that accepts an injectable ``httpx`` transport, and a
factory. Only read-only GET endpoints are used; credentials are never rendered.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any

from careeros.exceptions import CheckpointError

_GITHUB_HOST = "github.com"


class GitHubAccessError(CheckpointError):
    """Raised when GitHub read-only state cannot be obtained."""


def parse_github_slug(remote_url: str) -> str:
    """Extract ``owner/repo`` from a GitHub remote URL, or ``""`` if not GitHub."""
    url = (remote_url or "").strip()
    if not url:
        return ""
    host = ""
    if "://" in url:
        host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
    elif url.startswith("git@"):
        host = url.split("@", 1)[1].split(":", 1)[0]
    if host != _GITHUB_HOST:
        return ""
    match = re.search(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?\s*$", url)
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2)}"


class GitHubProvider(ABC):
    """Capability-oriented read-only GitHub interface."""

    name: str = "abstract"

    @abstractmethod
    def repo_slug(self) -> str:
        """Return the ``owner/repo`` slug this provider reads."""

    @abstractmethod
    def github_main_sha(self) -> str:
        """Return the SHA of ``main`` on GitHub."""

    @abstractmethod
    def github_main_commit_subject(self) -> str:
        """Return the first line of the latest ``main`` commit message."""

    @abstractmethod
    def latest_release(self) -> tuple[str, str]:
        """Return ``(tag_name, commit_sha)`` of the latest release, or ``("", "")``."""

    @abstractmethod
    def open_pull_requests(self) -> tuple[dict[str, str], ...]:
        """Return open PRs as ``{number, title, head, base}`` dicts."""


class HttpGitHubProvider(GitHubProvider):
    """GitHub API implementation backed by ``httpx`` with an injectable transport."""

    name = "github-http"

    def __init__(
        self,
        repo_slug: str,
        *,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        transport: Any | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._slug = repo_slug
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    def repo_slug(self) -> str:
        return self._slug

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get(self, path: str) -> Any:
        import httpx

        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.get(url, headers=self._headers())
                response.raise_for_status()
                return response.json()
        except GitHubAccessError:
            raise
        except Exception as exc:
            raise GitHubAccessError(f"GitHub API request failed for {path}: {exc}") from exc

    def github_main_sha(self) -> str:
        data = self._get(f"/repos/{self._slug}/commits/main")
        return str(data.get("sha", ""))

    def github_main_commit_subject(self) -> str:
        data = self._get(f"/repos/{self._slug}/commits/main")
        message = data.get("commit", {}).get("message", "")
        return str(message.splitlines()[0]) if message else ""

    def latest_release(self) -> tuple[str, str]:
        try:
            data = self._get(f"/repos/{self._slug}/releases/latest")
        except GitHubAccessError:
            return "", ""
        tag = str(data.get("tag_name", ""))
        if not tag:
            return "", ""
        commit = self._get(f"/repos/{self._slug}/commits/{tag}")
        return tag, str(commit.get("sha", ""))

    def open_pull_requests(self) -> tuple[dict[str, str], ...]:
        data = self._get(f"/repos/{self._slug}/pulls?state=open&per_page=100")
        out: list[dict[str, str]] = []
        for item in data or []:
            out.append(
                {
                    "number": str(item.get("number", "")),
                    "title": str(item.get("title", "")),
                    "head": str((item.get("head") or {}).get("ref", "")),
                    "base": str((item.get("base") or {}).get("ref", "")),
                }
            )
        return tuple(out)


def create_github_provider(
    repo_slug: str,
    *,
    token: str | None = None,
    transport: Any | None = None,
) -> GitHubProvider:
    """Create the default (HTTP) GitHub provider for a repository slug."""
    return HttpGitHubProvider(repo_slug, token=token, transport=transport)