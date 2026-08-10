"""Deterministic renderers for the Live Repository Checkpoint."""

from __future__ import annotations

import json

from .models import RepositoryCheckpoint


def _truncate(value: str, limit: int = 120) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def render_markdown(checkpoint: RepositoryCheckpoint) -> str:
    """Render the checkpoint as deterministic human-readable Markdown."""
    repo = checkpoint.repository
    local = checkpoint.local_git
    remote = checkpoint.remote
    doc = checkpoint.project_docs
    sync = checkpoint.sync

    lines: list[str] = []
    lines.append("# Live Repository Checkpoint")
    lines.append("")
    lines.append(f"- generated_at: `{checkpoint.generated_at}`")
    lines.append(f"- tool_version: `{checkpoint.tool_version}`")
    lines.append(f"- schema_version: `{checkpoint.schema_version}`")
    lines.append("")
    lines.append("## Repository")
    lines.append("")
    lines.append(f"- repo: `{repo.repo_name}`")
    lines.append(f"- local path: `{repo.local_path}`")
    lines.append(f"- remote: `{repo.remote_url}`")
    lines.append(f"- remote slug: `{repo.remote_slug}`")
    lines.append("")
    lines.append("## Local Git")
    lines.append("")
    lines.append(f"- current branch: `{local.current_branch}`")
    lines.append(f"- local HEAD: `{local.local_head_sha}`")
    lines.append(f"- recent commit: {_truncate(local.recent_commit_subject)}")
    if local.working_tree_clean:
        lines.append("- working tree: clean")
    else:
        lines.append(f"- working tree: {local.dirty_file_count} dirty file(s)")
    lines.append(f"- upstream: `{local.upstream_ref}`")
    lines.append(f"- local origin/main ref: `{local.local_origin_main_ref}`")
    lines.append("")
    lines.append("## Remote (GitHub)")
    lines.append("")
    if remote.error:
        lines.append(f"- error: {remote.error}")
    else:
        lines.append(f"- github main: `{remote.github_main_sha}`")
        lines.append(f"- github main commit: {_truncate(remote.github_main_commit_subject)}")
        lines.append(f"- latest release: `{remote.latest_release_tag}` -> `{remote.latest_release_sha}`")
        lines.append(f"- open PRs: {remote.open_pr_count}")
        for pr in remote.open_prs:
            lines.append(
                f"  - #{pr.get('number')} {_truncate(pr.get('title', ''), 80)} "
                f"({pr.get('head')} -> {pr.get('base')})"
            )
    lines.append("")
    lines.append("## Project-state documentation")
    lines.append("")
    lines.append(f"- docs found: {', '.join(doc.docs_found) if doc.docs_found else 'none'}")
    lines.append(f"- documented HEAD: `{doc.documented_head_sha}`")
    lines.append(f"- documented origin/main: `{doc.documented_origin_main_sha}`")
    lines.append(f"- documented latest tag: `{doc.documented_latest_tag}`")
    lines.append(f"- documented open PRs: {doc.documented_open_pr_count}")
    lines.append(f"- documented test status: {_truncate(doc.documented_test_status, 160)}")
    lines.append(f"- documented authorized action: {_truncate(doc.documented_authorized_action, 160)}")
    if doc.documented_deferred_items:
        lines.append("- documented deferred/preservation items:")
        for item in doc.documented_deferred_items:
            lines.append(f"  - {_truncate(item, 160)}")
    lines.append(f"- documented last checkpoint: {_truncate(doc.documented_last_checkpoint, 160)}")
    lines.append("")
    lines.append("## Synchronization")
    lines.append("")
    if sync.in_sync:
        lines.append(
            "- IN SYNC: no discrepancies detected between GitHub, local Git, and the "
            "project-state documentation."
        )
    else:
        lines.append("- DISCREPANCIES DETECTED (reported, not resolved):")
        for d in sync.discrepancies:
            lines.append(
                f"  - `{d.field}`: `{d.source_a}`=`{d.value_a}` vs "
                f"`{d.source_b}`=`{d.value_b}`"
            )
            if d.description:
                lines.append(f"    {d.description}")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    for field_name, source in checkpoint.provenance.items():
        lines.append(f"- {field_name}: {source}")
    lines.append("")
    return "\n".join(lines)


def render_json(checkpoint: RepositoryCheckpoint) -> str:
    """Render the checkpoint as deterministic JSON (keys sorted)."""
    return json.dumps(checkpoint.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)