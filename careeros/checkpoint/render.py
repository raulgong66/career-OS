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


def _pv(value: str, placeholder: str = "(unavailable)") -> str:
    text = (value or "").strip()
    return text if text else placeholder


def _pr_line(pr: dict[str, str]) -> str:
    number = (pr.get("number") or "").strip()
    title = _truncate(pr.get("title", ""), 80)
    head = (pr.get("head") or "").strip()
    base = (pr.get("base") or "").strip()
    route = f"({head} -> {base})" if head or base else ""
    if number and title:
        return f"#{number} {title} {route}".strip()
    if number:
        return f"#{number} {route}".strip()
    return title or route or "(unknown PR)"


def render_prompt(
    checkpoint: RepositoryCheckpoint,
    *,
    include_generated_at: bool = False,
) -> str:
    """Render the checkpoint as a copy/paste-ready New Chat bootstrap prompt.

    The output is deterministic plain text (no Markdown markup) so it can be
    pasted directly into a new ChatGPT session. ``generated_at`` is excluded by
    default to keep the prompt stable across runs. Each block is labelled with
    its provenance class (VERIFIED LIVE FACT / DOCUMENTED FACT / DISCREPANCY /
    UNAVAILABLE SOURCE); unavailable sources are reported as such and never
    replaced by invented values.
    """
    repo = checkpoint.repository
    local = checkpoint.local_git
    remote = checkpoint.remote
    doc = checkpoint.project_docs
    sync = checkpoint.sync

    lines: list[str] = []
    lines.append("NEW CHAT — CAREEROS LIVE REPOSITORY CONTEXT")
    lines.append("")
    if include_generated_at:
        lines.append(f"- generated_at: {checkpoint.generated_at}")
        lines.append("")
    lines.append(f"You are continuing work on the {_pv(repo.repo_name, 'CareerOS')} repository.")
    lines.append("")
    lines.append("IMPORTANT OPERATING RULES")
    lines.append("- Treat the repository facts below as the authoritative live checkpoint supplied by the repository tooling.")
    lines.append("- Do not assume stale local Git refs represent GitHub state.")
    lines.append("- Distinguish verified facts from discrepancies and unavailable sources.")
    lines.append("- Do not perform Git mutations unless explicitly authorized.")
    lines.append("- Do not fetch/pull/reset/rebase/merge/commit/push/tag unless explicitly authorized.")
    lines.append("- If repository state is ambiguous, report the ambiguity rather than guessing.")
    lines.append("")
    lines.append("REPOSITORY")
    lines.append(f"- Name: {_pv(repo.repo_name)}")
    lines.append(f"- Local path: {_pv(repo.local_path)}")
    lines.append(f"- Remote: {_pv(repo.remote_url)}")
    lines.append(f"- GitHub repository: {_pv(repo.remote_slug)}")
    lines.append("")
    lines.append("CURRENT LOCAL STATE  [VERIFIED LIVE FACT]")
    lines.append(f"- Branch: {_pv(local.current_branch)}")
    lines.append(f"- HEAD: {_pv(local.local_head_sha)}")
    lines.append(f"- Recent commit: {_truncate(local.recent_commit_subject) or '(unavailable)'}")
    if local.working_tree_clean:
        lines.append("- Working tree: clean")
        lines.append("- Dirty files: 0")
    else:
        lines.append("- Working tree: dirty")
        lines.append(f"- Dirty files: {local.dirty_file_count}")
    lines.append(f"- Local origin/main: {_pv(local.local_origin_main_ref)}")
    lines.append("")
    if remote.error:
        lines.append("CURRENT GITHUB STATE  [UNAVAILABLE SOURCE]")
        lines.append("")
        lines.append(f"- GitHub state unavailable: {remote.error}")
        lines.append("- Remote availability: unavailable")
        lines.append(f"- Remote error: {remote.error}")
    else:
        lines.append("CURRENT GITHUB STATE  [VERIFIED LIVE FACT]")
        lines.append("")
        lines.append(f"- GitHub main: {_pv(remote.github_main_sha)}")
        if remote.latest_release_tag:
            lines.append(f"- Latest release/tag: {remote.latest_release_tag} ({remote.latest_release_sha})")
        else:
            lines.append("- Latest release/tag: none")
        lines.append(f"- Open PRs: {remote.open_pr_count}")
        for pr in remote.open_prs:
            lines.append(f"  - {_pr_line(pr)}")
        lines.append("- Remote availability: available")
        lines.append("- Remote error: none")
    lines.append("")
    lines.append("PROJECT DOCUMENTATION STATE  [DOCUMENTED FACT]")
    lines.append("")
    lines.append(f"- Documented HEAD: {_pv(doc.documented_head_sha, '(not documented)')}")
    lines.append(f"- Documented origin/main: {_pv(doc.documented_origin_main_sha, '(not documented)')}")
    lines.append(f"- Documented latest tag: {_pv(doc.documented_latest_tag, '(not documented)')}")
    lines.append(
        f"- Documented test status: {_truncate(doc.documented_test_status, 160) or '(not documented)'}"
    )
    lines.append(
        f"- Documented authorized action: "
        f"{_truncate(doc.documented_authorized_action, 160) or '(not documented)'}"
    )
    if doc.documented_deferred_items:
        lines.append("- Deferred/preservation items:")
        for item in doc.documented_deferred_items:
            lines.append(f"  - {_truncate(item, 160)}")
    else:
        lines.append("- Deferred/preservation items: none")
    lines.append("")
    lines.append("RECONCILIATION  " + ("[DISCREPANCY]" if not sync.in_sync else "[IN SYNC]"))
    lines.append("")
    lines.append(f"- In sync: {'yes' if sync.in_sync else 'no'}")
    if sync.discrepancies:
        lines.append("- Discrepancies:")
        for d in sync.discrepancies:
            lines.append(f"  - {d.field}: {d.source_a}={d.value_a} vs {d.source_b}={d.value_b}")
            if d.description:
                lines.append(f"    {d.description}")
    else:
        lines.append("- Discrepancies: none")
    lines.append("")
    lines.append("VERIFICATION / PROVENANCE")
    lines.append("")
    for field_name, source in checkpoint.provenance.items():
        lines.append(f"- {field_name}: {source}")
    lines.append("")
    lines.append("CURRENT TASK")
    lines.append("Continue from the checkpoint above. Before proposing changes, understand the discrepancies and current repository state.")
    lines.append("")
    lines.append("END CHECKPOINT")
    lines.append("")
    return "\n".join(lines)