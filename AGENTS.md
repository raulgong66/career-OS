# AGENTS.md

## Project Governance

1. Read `docs/project/Project-Constitution.md` before starting any task.
2. Treat the Constitution as the authoritative source of project governance.
3. If a request conflicts with the Constitution, stop and explain the conflict.
4. Keep documentation consistent with the Constitution.

## Collaboration Rules

1. Prioritize truth over fluency.
2. Clearly distinguish verified facts from assumptions and recommendations.
3. Ask for clarification instead of making assumptions.
4. Keep recommendations evidence-based and state uncertainty explicitly.

## Capability Transparency

AI agents must clearly distinguish:

1. Actions they successfully performed.
2. Actions they are unable to perform.
3. Actions that require additional permissions or tools.

## Change Rules

1. Do not redesign the architecture unless explicitly requested.
2. Treat approved architecture documents as frozen until implementation reveals a problem.
3. Make small, cohesive, reviewable changes.
4. AI agents may create or amend local commits only when explicitly requested by the user.
5. AI agents must never push changes to the remote repository unless the user explicitly instructs them to do so and the required authentication and permissions are available.
6. If a push cannot be completed because of missing authentication, permissions, tooling, or other environmental limitations, clearly explain the reason and stop without attempting alternative publication methods.
7. Repository publication is a user-controlled action unless explicitly delegated.
8. Maintain a decision log for major architectural decisions.

## Project State Checkpoints

1. At the start of every session — and after any new chat, context, model, agent, or machine change — read `docs/project-state/CURRENT_STATE.md` and perform a fresh read-only repository checkpoint before continuing.
2. Treat `CURRENT_STATE.md` as the authoritative answer to "where are we". Verify its baseline against the repository: branch, HEAD SHA, origin/main, latest tag, and working-tree status.
3. Follow the checkpoint gates B1–B7 defined in `docs/development/PROJECT_OPERATIONS_MANUAL.md` at every implementation boundary.
4. Never infer a branch's purpose from a task description.
5. If branch purpose, ancestry, baseline, scope, or intended target is ambiguous: STOP and ask for clarification.
6. No implementation may begin until the target branch, baseline, authorized files, forbidden scope, and next authorized action are explicitly established.

## Pre-submit verification

Run these commands before considering a task complete:

```bash
cd C:\Users\raul\AI\careeros\career-OS
python -m pytest -v        # 555 tests expected (requires fastapi + httpx + python-multipart for full suite)
cd frontend
npm run build              # tsc + vite build
npm run lint               # oxlint (must be clean)
```
