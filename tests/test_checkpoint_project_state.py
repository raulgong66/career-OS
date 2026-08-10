"""Tests for the project-state documentation reader."""

from __future__ import annotations

from pathlib import Path

from careeros.checkpoint.project_state import ProjectStateReader

DOC = """# CareerOS — Current Project State

## HEAD SHA

- `f0340efd981a0b69947afcf4f952f9b78e1fa264` — GitHub `main` after the PR #11 merge

## origin/main SHA

- `f0340efd981a0b69947afcf4f952f9b78e1fa264` (GitHub `origin/main`)

## Latest tag

- `v1.27.0` — annotated tag (tag object `fe11d95a…`), points to `8adab82`, pushed to origin

## Open PRs

- None.

## Verified test status

Last verified on the PR #11 head at `4bf74e5` (2026-08-09), merged via PR #11:

- Backend: `python -m pytest -q` -> **1041 passed**

## Deferred / preservation items (recorded, NOT resolved in this task)

- `6e5281a` roadmap preservation decision — recorded, not yet applied/reviewed.
- `AGENTS.md` stale "555 tests expected" governance drift — documented, not corrected.

## Current authorized action

- Documentation-only: refresh `CURRENT_STATE.md` to reflect the merged PR #11.

## Last checkpoint / update

- 2026-08-09: `CURRENT_STATE.md` created as part of the Project State Checkpoint System.
- 2026-08-09: refreshed after PR #11 merge (`dc8242b`).
"""


def _write(tmp_path: Path, text: str) -> Path:
    state_dir = tmp_path / "docs" / "project-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "CURRENT_STATE.md"
    path.write_text(text, encoding="utf-8")
    (state_dir / "M1.27-STATE.md").write_text("# M1.27\n", encoding="utf-8")
    return tmp_path


def test_reads_sections(tmp_path: Path) -> None:
    root = _write(tmp_path, DOC)
    state = ProjectStateReader(root).read_current_state()
    assert state.documented_head_sha == "f0340efd981a0b69947afcf4f952f9b78e1fa264"
    assert state.documented_origin_main_sha == "f0340efd981a0b69947afcf4f952f9b78e1fa264"
    assert state.documented_latest_tag == "v1.27.0"
    assert state.documented_open_pr_count == "None."
    assert "1041 passed" in state.documented_test_status
    assert len(state.documented_deferred_items) == 2
    assert "6e5281a" in state.documented_deferred_items[0]
    assert "refreshed after PR #11 merge" in state.documented_last_checkpoint
    assert "M1.27-STATE.md" in state.docs_found


def test_missing_file_yields_empty_state(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    state = ProjectStateReader(root).read_current_state()
    assert state.documented_head_sha == ""
    assert state.docs_found == ()


def test_partial_document(tmp_path: Path) -> None:
    root = _write(tmp_path, "## HEAD SHA\n\n- `abc1234`\n")
    state = ProjectStateReader(root).read_current_state()
    assert state.documented_head_sha == "abc1234"
    assert state.documented_origin_main_sha == ""
    assert state.documented_deferred_items == ()