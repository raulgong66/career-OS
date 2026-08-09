# CareerOS — Current Project State

> Canonical, always-current project-state snapshot for the CareerOS repository.
> Maintained as part of the Project State Checkpoint System (checkpoint gates B1–B7 are
> defined in `docs/development/PROJECT_OPERATIONS_MANUAL.md`).
> This is a factual snapshot, not a design document or conversational reasoning.

## Repository

- Repo: `career-OS`
- Remote: `origin` → `https://github.com/raulgong66/career-OS.git`
- Local path: `C:\Users\raul\AI\careeros\career-OS`

## Canonical branch

- `main`

## HEAD SHA

- `8adab822f605a6203bfe931a4193ffe517e75d79`

## origin/main SHA

- `8adab822f605a6203bfe931a4193ffe517e75d79` (in sync with local `main`)

## Latest tag

- `v1.27.0` — annotated tag (tag object `fe11d95a…`), points to `8adab82`, pushed to origin

## Latest release

- GitHub Release **v1.27.0** — https://github.com/raulgong66/career-OS/releases/tag/v1.27.0

## Latest completed milestone

- **M1.27 — CSKS Incremental Indexing** — COMPLETE and RELEASED as v1.27.0.
  See `docs/project-state/M1.27-STATE.md`.

## Working-tree status

- Clean. `git status --porcelain` is empty; no uncommitted changes.

## Open PRs

- None.

## Relevant retained branches

- `feature/m1.27-csks-incremental-indexing` → `f3f8dcf7…` (M1.27, merged via PR #7)
- `feature/tailored-cv-deduplication` → `e742b4f4…` (CV dedup work, merged via PR #8)
- `feature/tailored-cv-deduplication-pr` → `d6fc3522…` (CV dedup PR branch)
- `feature/ui-restoration` → `c07eabc0…` (restored-UI work, merged via PR #9)
- `feature/ui-restoration-pr` → `c0a68638…` (UI restoration PR branch)

## Verified test status

Last verified on `main` at `8adab82` (2026-08-09):

- Backend: `python -m pytest -q` → **1007 passed** (1 warning)
- Frontend: typecheck PASS · **61 tests (5 files) PASS** · lint PASS · build PASS

## Completed work

- M1.27 — CSKS Incremental Indexing (PR #7, merge `782464c3`) — released as v1.27.0.
- Tailored-CV duplicate-narrative suppression (PR #8, merge `80b2dc8`).
- Frontend UI restoration (PR #9, merge `8adab82`).
- Annotated tag `v1.27.0` created on `8adab82` and GitHub Release published.

## Pending work

- None. No implementation task is currently authorized, so there is nothing pending.
- Planning-only candidates (not authorized): M1.28 and beyond, per `docs/platform-beta/`.

## Explicitly excluded / do-not-touch work

- Application code: `careeros/`, `api/`, `frontend/`, `tests/`, `profiles/`, `schemas/`, `data/`,
  `careeros_cli/`, `reasoning/`, DOCX generation, CSKS implementation, application configuration.
- Existing feature branches, tags/releases, PR history.
- No commit, push, PR, or new tag/release without explicit authorization.

## Current authorized action

- Documentation/governance only: establish the Project State Checkpoint System
  (`CURRENT_STATE.md`, `M1.27-STATE.md`, and governance-document wiring).
- Next commit/push is BLOCKED pending explicit review and authorization.

## Required baseline

- `main` = `origin/main` = `8adab822f605a6203bfe931a4193ffe517e75d79`
- Working tree clean · `v1.27.0` points to `8adab82` · no open PRs
- Any deviation from this baseline must be reconciled with this file before work proceeds.

## Last checkpoint / update

- 2026-08-09: `CURRENT_STATE.md` created as part of the Project State Checkpoint System
  (documentation-only change; commit pending review).

## Milestone numbering

Milestone references in this project use implementation milestone numbering (`M1.<xx>`,
e.g. `M1.27`). The planning-scheme numbering (`M1`–`M5` in `docs/platform-beta/Milestones.md`)
is distinct and does not map 1:1 to implementation milestones — see the mapping in
`docs/development/PROJECT_OPERATIONS_MANUAL.md`.
