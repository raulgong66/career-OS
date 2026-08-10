"""Source-of-truth / conflict detection for the Live Repository Checkpoint.

Every fact in a checkpoint has a primary (authoritative) source and may also be
recorded in secondary sources (local Git refs, documentation). This module
computes, from an already-collected checkpoint, the discrepancies between those
sources. It never resolves a conflict — it only reports it.
"""

from __future__ import annotations

import re

from .models import Discrepancy, LocalGitState, ProjectDocState, RemoteGitHubState, SyncState


def _parse_doc_open_pr_count(raw: str) -> int | None:
    """Parse an 'Open PRs' doc value into an integer, or ``None`` if unparseable."""
    text = (raw or "").strip().lower()
    if not text:
        return None
    if text == "none" or text.startswith("none"):
        return 0
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group())


def detect_discrepancies(
    local: LocalGitState,
    remote: RemoteGitHubState,
    doc: ProjectDocState,
) -> tuple[Discrepancy, ...]:
    """Return every detected conflict between authoritative and secondary sources.

    Arguments are the already-collected state blocks; the function is pure so it
    can be unit-tested without any I/O. Conflicts are reported as-is and never
    resolved here.
    """
    out: list[Discrepancy] = []

    if remote.error:
        out.append(
            Discrepancy(
                field="github",
                source_a="github",
                value_a="unavailable",
                source_b="required",
                value_b="readable",
                description=remote.error,
            )
        )

    if (
        remote.github_main_sha
        and local.local_origin_main_ref
        and remote.github_main_sha != local.local_origin_main_ref
    ):
        out.append(
            Discrepancy(
                field="github main",
                source_a="github",
                value_a=remote.github_main_sha,
                source_b="local origin/main",
                value_b=local.local_origin_main_ref,
                description="Local origin/main ref is stale relative to GitHub main.",
            )
        )

    if (
        remote.github_main_sha
        and doc.documented_origin_main_sha
        and remote.github_main_sha != doc.documented_origin_main_sha
    ):
        out.append(
            Discrepancy(
                field="origin/main",
                source_a="github",
                value_a=remote.github_main_sha,
                source_b="CURRENT_STATE.md",
                value_b=doc.documented_origin_main_sha,
                description="CURRENT_STATE.md origin/main SHA is stale relative to GitHub.",
            )
        )

    if local.local_head_sha and doc.documented_head_sha and local.local_head_sha != doc.documented_head_sha:
        out.append(
            Discrepancy(
                field="HEAD",
                source_a="local_git",
                value_a=local.local_head_sha,
                source_b="CURRENT_STATE.md",
                value_b=doc.documented_head_sha,
                description="CURRENT_STATE.md HEAD SHA does not equal the local HEAD.",
            )
        )

    if remote.latest_release_tag and doc.documented_latest_tag and remote.latest_release_tag != doc.documented_latest_tag:
        out.append(
            Discrepancy(
                field="latest tag",
                source_a="github",
                value_a=remote.latest_release_tag,
                source_b="CURRENT_STATE.md",
                value_b=doc.documented_latest_tag,
                description="CURRENT_STATE.md latest tag is stale relative to GitHub.",
            )
        )

    if not local.working_tree_clean:
        out.append(
            Discrepancy(
                field="working tree",
                source_a="local_git",
                value_a=f"{local.dirty_file_count} dirty files",
                source_b="expected",
                value_b="clean working tree",
                description="Working tree is not clean.",
            )
        )

    doc_open_pr_count = _parse_doc_open_pr_count(doc.documented_open_pr_count)
    if doc_open_pr_count is not None and not remote.error and remote.open_pr_count != doc_open_pr_count:
        out.append(
            Discrepancy(
                field="open PRs",
                source_a="github",
                value_a=str(remote.open_pr_count),
                source_b="CURRENT_STATE.md",
                value_b=str(doc_open_pr_count),
                description="CURRENT_STATE.md open-PR count is stale relative to GitHub.",
            )
        )

    return tuple(out)


def compute_sync_state(
    local: LocalGitState,
    remote: RemoteGitHubState,
    doc: ProjectDocState,
) -> SyncState:
    """Compute the synchronization status from the three state blocks."""
    discrepancies = detect_discrepancies(local, remote, doc)
    return SyncState(in_sync=len(discrepancies) == 0, discrepancies=discrepancies)