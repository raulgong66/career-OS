# CareerOS — Project Operations Manual

Version: 2026-08-02
Maintainer: Platform Beta Engineering

This living operations manual documents the official branch, release, and review workflows, the roles and responsibilities for AI agents operating on this repository, and the recovery and verification procedures required for safe, auditable project operations. It is written to allow any agent or engineer to recover project state and perform routine operations without chat history.

---

## Table of contents

- Official branch strategy
- Roles and responsibilities (ChatGPT, Copilot, OpenCode)
- Standard milestone workflow
- Context recovery procedure for a new AI session
- Mandatory verification checklist (before and after implementation)
- Project state checkpoint system
- Branch synchronization and recovery (Mac <> Windows)
- Checkpoint tag and GitHub Release policy
- Architecture guardrails
- Standard operating procedures for reviews, merges, and releases

---

## Official branch strategy

- `main` — protected release-ready branch. Only merged from release branches after QA and sign-off. Tagged releases are cut from `main`.
- `develop` (optional) — integration branch for long-running development, if used by the team. Not required for short-lived feature work.
- `feature/*` — short-lived feature branches. Branch names use the pattern `feature/<milestone>-<short-desc>` (e.g. `feature/m1.21-artifact-workspace`).
- `release/*` — branch created to prepare a release (optional). Used to stabilize, run final regression, and apply release metadata.
- `hotfix/*` — branches created from `main` for urgent production fixes.
- `origin/*` — remote-tracking branches on GitHub.

Branch protection rules (recommended):
- `main` and `release/*` protected: require PR review (2 reviewers), passing CI, and signed commits if required.
- Direct pushes to `main` are disabled for contributors.

Tagging strategy:
- Use semantic or milestone-checkpoint tags, e.g. `m1.21-artifact-workspace` for milestone checkpoints and `v1.2.0` for release versions.
- Every milestone checkpoint tag must include an associated GitHub Release note summarizing the scope and acceptance criteria.

---

## Roles and responsibilities for AI agents

This project recognizes three agent archetypes. Their responsibilities are explicit and limited to reduce accidental scope creep.

- ChatGPT (general assistant):
  - Role: high-level guidance, architecture reviews, documentation authoring, and non-committal code suggestions.
  - Responsibilities: produce design docs, milestone specifications, architecture reviews, and code review summaries.
  - Constraints: must not directly push changes without explicit human approval; when automating commits, follow the `Change Rules` in `AGENTS.md` and require explicit user acknowledgment.

- Copilot (developer assistant within editor):
  - Role: in-editor code completions and developer ergonomics.
  - Responsibilities: suggest code snippets, implement small refactors, and scaffold tests per developer prompts.
  - Constraints: should respect repository conventions and not modify high-level architectural boundaries without human approval.

- OpenCode (automation agent / CI automation):
  - Role: run automated tasks, batch code updates, and execute multi-file edits under explicit instructions.
  - Responsibilities: run CI, format code, apply mechanical changes, and perform batch upgrades.
  - Constraints: must record exact changes, produce a summary, and request PR creation or human review for any change that affects architecture or public APIs.

Common rules for all agents:
- Always preserve the canonical profile and Core boundaries (see Architecture Guardrails below).
- Distinguish between suggested code and committed code. Human approval is required for merging PRs or pushing tags.
- When performing automated edits, create a clear commit message and a concise summary of the change in the PR body.

---

## Standard milestone workflow

1. Author milestone spec (`docs/platform-beta/M1.xx-*.md`) describing objective, user workflows, architecture, constraints, acceptance criteria, and tests.
2. Create a `feature/<milestone>` branch from the latest `feature/platform-beta-architecture` or `develop` branch as agreed.
3. Implement changes in small commits, keeping domain and API responsibilities separate.
4. Add or update tests (unit + integration) that validate domain behavior and API contracts.
5. Run local CI: `python -m pytest -v` (backend tests), `npm run build` and `npm run lint` (frontend). Fix issues until CI is green locally.
6. Create a PR targeting `feature/platform-beta-architecture` or `develop` as per project rules. Include the milestone spec in the PR description.
7. Architecture review: at least one domain maintainer and one platform architect must approve.
8. Merge after CI passes and approvals are recorded.
9. Create a milestone checkpoint tag `m<milestone>-<description>` and publish a GitHub Release with release notes summarizing acceptance criteria and test outcomes.

Notes:
- Milestones that introduce domain changes require an Architecture Compliance Review and updated ADRs when applicable.
- Keep changes small and atomic to simplify reviews.

---

## Context recovery procedure for a new AI session

When an agent or developer begins work on this repo without prior chat context, follow these steps to recover the project state and context.

0. Read `docs/project-state/CURRENT_STATE.md` and verify its baseline against the repository (checkpoint gate B7).

1. Checkout the repository and fetch origin:

```bash
git fetch origin --prune
```

2. Determine the active branch for Platform Beta work:
- Inspect `git branch -a` and prefer `feature/platform-beta-architecture` or `develop` as the current integration branch.

3. Inspect recent commits and tags:

```bash
git log --oneline -n 20
git tag --list --sort=-creatordate
```

4. Read milestone specs in `docs/platform-beta/` for current priorities.

5. Rebuild and run tests locally:
- Backend:

```bash
python -m pytest -v
```

- Frontend:

```bash
cd frontend
npm ci
npm run build
npm run lint
```

6. Locate key entry points and boundaries:
- API surface: `api/main.py` and `api/*.py`.
- Domain: `careeros/` directory.
- Frontend: `frontend/src/`.
- Canonical profile examples: `profiles/`.

7. If further clarification is needed, run architecture checks (automated scripts or Copilot checks) and consult `AGENTS.md`.

---

## Mandatory verification checklist (before and after implementation)

Before merging any feature or milestone PR, ensure the following checks are performed and documented in the PR description:

- [ ] Tests: unit tests added/updated and `pytest` passes locally.
- [ ] Frontend build: `npm run build` completes without errors.
- [ ] Linting: `npm run lint` is clean.
- [ ] Architecture compliance: domain logic stays in `careeros/` only.
- [ ] API transport: `api/` implements only transport and DTO mapping.
- [ ] Canonical profile: no mutation of canonical profile files in `profiles/` unless explicitly part of a resolution workflow.
- [ ] No AI provider keys or SDKs added to code or CI secrets without explicit approval.
- [ ] Documentation: milestone spec included and updated in `docs/platform-beta/`.
- [ ] PR description includes a short test matrix and rollout/rollback notes.

After merge and release, validate:

- [ ] CI green for merge commit.
- [ ] Tag exists and Release notes published.
- [ ] Quick smoke test: critical API endpoints and frontend routes respond correctly.
- [ ] Update milestone doc with actual verification results and timestamps.
- [ ] Update `docs/project-state/CURRENT_STATE.md` and the milestone `M<ver>-STATE.md` to reflect the merge/release.

---

## Project state checkpoint system

State files live in `docs/project-state/`:

- `docs/project-state/CURRENT_STATE.md` — the always-current factual snapshot (branch, HEAD SHA, origin/main, latest tag/release, milestone, working-tree status, open PRs, verified test status, completed/pending/excluded work, current authorized action, required baseline, last checkpoint). It is a factual snapshot, not conversational reasoning.
- `docs/project-state/M<ver>-STATE.md` — one per implementation milestone (e.g. `M1.27-STATE.md`). Created at milestone start, updated at every checkpoint boundary, frozen when the milestone is released.

Checkpoint gates (STOP-and-record at each boundary):

1. **Before implementation** — perform a mandatory read-only PROJECT STATE CHECKPOINT: read `CURRENT_STATE.md`, verify the baseline (branch, HEAD SHA, origin/main, latest tag, clean working tree), and confirm the scope.
2. **After reconnaissance / scope decision** — record the approved scope before implementation begins.
3. **Before commit** — verify branch, HEAD/base, authorized files, test results, and absence of out-of-scope contamination.
4. **Before PR** — verify the PR diff against the intended base and the exact authorized scope.
5. **After merge** — verify the resulting `main` SHA and integration tests.
6. **After tag/release** — verify the tag points to the intended release commit.
7. **New chat / context / model / agent / machine** — read `CURRENT_STATE.md` and perform a fresh repository checkpoint before continuing.

Working rules:

- Never infer branch intent from a task description.
- If branch purpose, ancestry, baseline, scope, or intended target is ambiguous: STOP and ask for clarification.
- No implementation may begin until the target branch, baseline, authorized files, forbidden scope, and next authorized action are explicitly established.

Milestone numbering — planning vs implementation:

| Scheme | Format | Example | Used in |
|---|---|---|---|
| Planning milestone numbering | `M1`–`M5` | `M3 — Professional Intelligence` | `docs/platform-beta/Milestones.md` — capability workstream planning, not delivery commitments |
| Implementation milestone numbering | `M1.<xx>` | `M1.27 — CSKS Incremental Indexing` | Feature branches (`feature/m1.27-*`), milestone specs, checkpoint tags, release versions (`v1.27.0`), `M<ver>-STATE.md` files |

Implementation milestone numbers do not map 1:1 to planning milestone numbers. Verify the specific milestone before assuming scope.

---

## Branch synchronization and recovery (Mac <> Windows)

Typical issues arise from line ending normalization and case-insensitive filesystems.

Recommended configuration:
- Ensure consistent `core.autocrlf` setting across platforms (team decision). Recommended: commit with `LF` in repo and set `core.autocrlf` to `input` on macOS and `true` on Windows if contributors expect CRLF at checkout.

Sync procedure:
1. On macOS or Linux:

```bash
git fetch origin --prune
git checkout feature/platform-beta-architecture
git pull --ff-only origin/feature/platform-beta-architecture
```

2. On Windows (PowerShell / Git Bash):

```powershell
git fetch origin --prune
git checkout feature/platform-beta-architecture
git pull --ff-only origin/feature/platform-beta-architecture
```

3. If branch diverges and a fast-forward is not possible:
- Rebase local changes onto the updated remote if the commits are local and not shared:

```bash
git fetch origin
git rebase origin/feature/platform-beta-architecture
```

- If local and remote have different unrelated commits, prefer creating a new branch and opening a PR. Do not force-push to shared branches.

Resolving case-only filename issues:
- On Windows, rename the file to a temporary name, commit, push, then rename back on macOS and commit, to avoid git treating case-only renames as no-op.

---

## Checkpoint tag and GitHub Release policy

- Milestone checkpoint tags (e.g. `m1.21-artifact-workspace`) are created when the milestone's acceptance criteria pass and reviewers sign off.
- A GitHub Release must be published for each checkpoint tag containing:
  - Milestone summary
  - Acceptance criteria and pass/fail status
  - Test matrix and key test outputs (CI pass, smoke tests)
  - Rollback instructions if applicable
- Semver releases (e.g. `v1.2.0`) are created from `main` after release verification and QA.

---

## Architecture guardrails

- Frontend (`frontend/src/`) = Presentation only. It may call services and render server-provided payloads, but must not implement domain business logic (e.g., evaluation, scoring, generation rules).
- API (`api/`) = Transport only. It validates requests, maps DTOs, and delegates work to the Domain. No report assembly or domain logic in API layer.
- Domain (`careeros/`) = Business logic owner. Implements canonical profile handling, reasoning engine, artifact generation, session lifecycle, evaluation, and export pipelines.
- Canonical Profile (`profiles/` + `schemas/profile.schema.json`) = Single source of truth for professional data. Derived artifacts and runtime sessions must reference canonical elements by ID and evidence references (ADR-002). Canonical profile mutation is only allowed through explicit resolution workflows.

Dependency flow must remain strictly:

```
Frontend (UI)
  ↓
API (transport)
  ↓
Domain (business logic / Core)
  ↓
Persistence (profiles/, data/)
```

No lateral bypassing of layers is allowed.

---

## Standard operating procedures for reviews, merges, and releases

- PR creation:
  - Title prefixed with `feat:`, `fix:`, `docs:`, or `chore:` as appropriate.
  - Link milestone spec and include a test matrix and rollout plan.
  - Assign at least two reviewers: one domain reviewer and one platform reviewer.

- Review process:
  - Reviewer checks: tests, architecture compliance, DTO boundaries, API contracts, and doc updates.
  - If substantial architecture changes are included, request an Architecture Compliance Review (ACR).

- Merge policy:
  - Merge only after approvals and passing CI.
  - Prefer merge strategy `--no-ff` to preserve PR history, unless repository policy states otherwise.

- Post-merge actions:
  - Create checkpoint tag if milestone completed.
  - Publish GitHub Release with notes and verification outputs.

- Emergency hotfix:
  - Create `hotfix/<short-desc>` from `main`, commit, run CI, and create a PR to `main` and backport to `develop` or `feature/platform-beta-architecture` as needed.

---

## Appendix: Quick commands

Fetch and fast-forward a branch:

```bash
git fetch origin --prune
git checkout feature/platform-beta-architecture
git merge --ff-only origin/feature/platform-beta-architecture
```

Run backend tests:

```bash
python -m pytest -v
```

Run frontend build and lint:

```bash
cd frontend
npm ci
npm run build
npm run lint
```

Create a checkpoint tag and push:

```bash
git tag -a m1.21-artifact-workspace -m "M1.21 Artifact Workspace checkpoint"
git push origin m1.21-artifact-workspace
```

---

This document is a living manual: update it whenever operational procedures, branch strategy, or agent responsibilities change. Store any procedural exceptions and decision logs adjacent to `docs/project/` or in `AGENTS.md` for auditability.
