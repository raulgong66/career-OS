"""Tests for the read-only GitHub provider and slug parsing.

The HTTP provider is exercised through ``httpx.MockTransport`` (no network),
mirroring the pattern used in ``test_ai_provider.py``.
"""

from __future__ import annotations

import httpx
import pytest

from careeros.checkpoint.github import (
    GitHubAccessError,
    HttpGitHubProvider,
    create_github_provider,
    parse_github_slug,
)

SLUG = "raulgong66/career-OS"


def _provider(handler) -> HttpGitHubProvider:
    return HttpGitHubProvider(SLUG, token="ghp_test", transport=httpx.MockTransport(handler))


def test_parse_github_slug() -> None:
    assert parse_github_slug("https://github.com/raulgong66/career-OS.git") == SLUG
    assert parse_github_slug("git@github.com:raulgong66/career-OS.git") == SLUG
    assert parse_github_slug("https://example.com/x/y.git") == ""
    assert parse_github_slug("") == ""


def test_github_main_sha_and_subject() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/raulgong66/career-OS/commits/main"
        assert request.headers["Authorization"] == "Bearer ghp_test"
        return httpx.Response(
            200,
            json={
                "sha": "f" * 40,
                "commit": {"message": "Merge pull request #12\n\nbody"},
            },
        )

    provider = _provider(handler)
    assert provider.github_main_sha() == "f" * 40
    assert provider.github_main_commit_subject() == "Merge pull request #12"


def test_latest_release() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json={"tag_name": "v1.27.0"})
        if request.url.path.endswith("/commits/v1.27.0"):
            return httpx.Response(200, json={"sha": "8" * 40})
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = _provider(handler)
    assert provider.latest_release() == ("v1.27.0", "8" * 40)


def test_latest_release_missing_returns_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    provider = _provider(handler)
    assert provider.latest_release() == ("", "")


def test_open_pull_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/raulgong66/career-OS/pulls"
        return httpx.Response(
            200,
            json=[
                {"number": 12, "title": "docs: refresh", "head": {"ref": "docs/x"}, "base": {"ref": "main"}},
                {"number": 13, "title": "feat: y", "head": {"ref": "feature/y"}, "base": {"ref": "main"}},
            ],
        )

    prs = _provider(handler).open_pull_requests()
    assert len(prs) == 2
    assert prs[0] == {"number": "12", "title": "docs: refresh", "head": "docs/x", "base": "main"}


def test_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    provider = _provider(handler)
    with pytest.raises(GitHubAccessError):
        provider.github_main_sha()


def test_factory_returns_http_provider() -> None:
    assert isinstance(create_github_provider(SLUG), HttpGitHubProvider)


def test_no_token_no_auth_header() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"sha": "f" * 40, "commit": {"message": "m"}})

    provider = HttpGitHubProvider(SLUG, transport=httpx.MockTransport(handler))
    provider.github_main_sha()
    assert captured["auth"] is None