# AI Workflow for CareerOS

## 1. Purpose

This document describes how AI tools should collaborate during the development and maintenance of CareerOS. It complements the project constitution, agent guidance, and the canonical profile model by turning governance into an operating workflow for day-to-day work.

## 2. Guiding Principles

- Keep the repository aligned with the project constitution and the current architectural vision.
- Treat approved documents as stable unless implementation reveals a real problem.
- Separate facts, assumptions, and recommendations clearly.
- Prefer evidence-based changes over speculative edits.
- Keep the canonical profile as the source of truth for professional facts; generated artifacts should remain derived views.
- Make small, reviewable changes and document significant decisions.

## 3. Roles and Responsibilities

### Human (Repository Owner)
- Owns the final intent, priorities, and acceptance of changes.
- Makes decisions about scope, tone, publishing, and release readiness.
- Provides explicit direction when a change requires commits, pushes, or new architecture decisions.

### ChatGPT
- Helps plan, summarize, explain, and draft content.
- Can propose implementation steps, review documentation, and clarify requirements.
- Should surface uncertainty and avoid making unilateral architectural decisions.

### Claude Code CLI
- Executes repository changes, edits, and local automation tasks.
- Should prefer small, auditable changes and keep the work traceable.
- Must not publish remotely unless explicitly instructed and permitted by authentication and access.

### GitHub Copilot
- Assists in code editing, refactoring, and routine development tasks inside the workspace.
- Works best when paired with explicit task boundaries and clear acceptance criteria.
- Should support the workflow without bypassing review or governance expectations.

## 4. Standard Development Workflow

1. Read `docs/project-state/CURRENT_STATE.md` and verify a fresh read-only repository checkpoint before starting (checkpoint gates B1–B7 are defined in `docs/development/PROJECT_OPERATIONS_MANUAL.md`).
2. Review the relevant guidance in the constitution and agent instructions before starting.
3. Clarify the task, scope, and expected outcome with the repository owner.
4. Record the approved scope before implementation begins.
5. Make the smallest change that addresses the request.
6. Keep documentation, schemas, and repository structure consistent with existing conventions.
7. Validate the result locally and explain any limitations or assumptions.
8. Present the change clearly so the human can review and approve it.

## 5. Decision Ownership

The human repository owner remains the final decision-maker for project direction, publication choices, and significant architecture changes. AI tools may recommend options, but they should not treat recommendations as final policy.

When a change affects the structure of CareerOS, the canonical profile model, or the documented workflow, the decision should be recorded in the project decision log rather than handled informally.

## 6. Code Review Strategy

- Review changes for correctness, clarity, and consistency with the existing repository structure.
- Check that documentation remains aligned with the constitution and the canonical profile model.
- Prefer concise diffs and avoid unrelated changes.
- Flag missing context, unsupported claims, or risky assumptions before accepting the work.
- If a change affects public-facing artifacts or repository structure, confirm that the human owner approves it.

## 7. Git Workflow

- AI tools may create or amend local commits only when explicitly requested by the user.
- Before creating a commit or PR, verify the branch, HEAD/base, authorized files, test results, and that no out-of-scope files were contaminated (checkpoint gates B3–B4).
- AI tools must not push to the remote repository unless the user explicitly instructs them to do so and the required authentication and permissions are available.
- If a push cannot proceed because of missing authentication, permissions, tooling, or other environment limitations, the limitation should be explained clearly and the workflow should stop without trying alternative publication methods.
- Repository publication remains a user-controlled action unless it is explicitly delegated.

## 8. Future AI Agents

Future AI agents should follow the same pattern: assist locally, stay transparent about what they can and cannot do, and defer high-impact decisions to the human owner. They should be expected to work within the same governance boundaries as current tools and to preserve the repository’s role as a structured career operating system rather than a generic file dump.
