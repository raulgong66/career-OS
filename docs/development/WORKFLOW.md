# CareerOS Engineering Workflow

This document defines the standard engineering process for CareerOS development. It is the official workflow for platform evolution and engineering operations, and it should be followed for all future work on the platform.

## Engineering Governance

CareerOS engineering is governed by four document layers.

1. `MANIFESTO.md`

   Defines the long-term philosophy of CareerOS.

2. Architecture Decision Records (ADRs)

   Capture permanent architectural decisions and their rationale.

3. Engineering Workflow (this document)

   Defines the engineering process used to evolve the platform.

4. Architecture Documentation

   Describes the current implementation and technical structure.

Manifesto
↓
ADRs
↓
Engineering Workflow
↓
Implementation

When conflicts arise, higher-level documents take precedence unless intentionally superseded by a new approved ADR.

## 1. Engineering Philosophy

CareerOS follows a deliberate architecture-first development model. Architecture is designed before implementation, and implementation validates architecture. Technical decisions are guided by the project Manifesto and approved Architecture Decision Records.

Principle:

"Architecture should lead implementation. Implementation should validate architecture."

The engineering workflow is not a feature checklist. It is the disciplined process by which platform evolution occurs.

## 2. Development Lifecycle

The standard CareerOS development lifecycle is:

Architecture Design
↓
Architecture Review
↓
Architecture Frozen
↓
Implementation Planning
↓
Implementation
↓
Testing
↓
Code Review
↓
Release Checkpoint
↓
Architecture Validation
↓
Next Milestone

- Architecture: define the technical scope, boundaries, and intended behavior of the next platform capability.
- ADR: document decisions that affect platform architecture, interfaces, or long-term maintainability.
- Architecture Review: verify the design against manifesto principles, ADRs, and module boundaries.
- Architecture Frozen: lock the approved architecture before implementation begins.
- Implementation Planning: translate architecture into a concrete delivery plan, scope, and verification approach.
- Implementation: build the platform behavior according to the agreed architecture and implementation plan.
- Testing: verify correctness with automated tests, integration checks, and validation of architectural invariants.
- Code Review: inspect implementation for architecture compliance, consistency, and quality.
- Release Checkpoint: finalize a milestone with a clean repository state, validated tests, and an annotated release tag.
- Architecture Validation: verify the implementation against the frozen architecture and update or extend architecture documents if needed.
- Next Milestone: use the release checkpoint as the baseline for the next architecture-driven cycle.

An implementation milestone may only begin after the corresponding architecture has reached the Architecture Frozen state.

Project State Checkpoints: every boundary in this lifecycle — before implementation, after scope decision, before commit, before PR, after merge, after tag/release, and on a new session/context/model/agent/machine — is a checkpoint gate. At each gate, read and update `docs/project-state/CURRENT_STATE.md` (and the active `docs/project-state/M<ver>-STATE.md`), verify the baseline, and stop if anything is ambiguous. The gates are defined in `docs/development/PROJECT_OPERATIONS_MANUAL.md`.

## 3. Workstation Responsibilities

CareerOS uses a dual-workstation model for role separation.

Windows workstation
- Primary implementation
- Feature development
- Unit tests
- Integration
- Bug fixing
- Release preparation

Mac workstation
- Architecture
- ADRs
- Documentation
- Technical research
- Code reviews
- QA
- Future milestone planning

Implementation may occasionally occur on the Mac when it is intentionally planned and aligned with architecture work. However, implementation ownership normally remains with the Windows workstation.

## 4. Branch Strategy

The current branch model is:

- `feature/platform-beta`
  - Primary implementation branch for the active milestone.
- `feature/platform-beta-architecture`
  - Architecture and documentation branch for platform design, ADRs, reviews, and future milestone preparation.
- `archive/*`
  - Historical preservation branches for work that must be retained without affecting active development.
- `main`
  - Future stable releases and platform baselines.

Each branch has a distinct purpose. The architecture branch remains separate from implementation history, while archive branches preserve historical work safely.

## 5. Synchronization Workflow

The synchronization process is:

Windows:
- implement milestone
- commit
- push

Mac:
- fetch latest changes
- checkout `feature/platform-beta-architecture`
- merge `origin/feature/platform-beta`
- review implementation
- prepare next milestone

Once both branches contain independent architecture work, normal merges are preferred over `--ff-only`. A standard merge preserves the independent history of the architecture branch and the implementation branch.

## 6. Commit Guidelines

Recommended commit conventions:

- `feat(...)`
- `fix(...)`
- `docs(...)`
- `refactor(...)`
- `test(...)`
- `adr(...)`
- `review(...)`

Commits should represent milestone-sized, coherent changes rather than large undifferentiated batches.

## 7. Architecture Review Checklist

Every review should verify:

- Manifesto compliance
- ADR compliance
- Canonical Profile remains the only source of truth
- Evidence model respected
- Claim model respected
- Provider agnosticism preserved
- Core/module boundaries respected
- No duplicated knowledge
- Human review remains authoritative

## 8. Release Management

Every significant platform milestone should conclude with:

- a clean repository
- complete automated tests
- an annotated Git tag
- a GitHub Release

Releases are immutable engineering checkpoints and synchronization baselines for all development environments.

## 9. Engineering Principles

CareerOS engineering decisions are governed by principles in `MANIFESTO.md` and the approved ADRs. Key principles include:

- Architecture First
- Knowledge Before Documents
- Evidence Before Claims
- Deterministic Reasoning Before AI
- AI Is a Consumer
- Human Review
- Provider Agnosticism
- Modular Evolution
- Long-Term Maintainability

These principles guide technical decisions without repeating the full manifesto text.

## 10. Future Evolution

This workflow is expected to evolve as CareerOS grows. Future contributors should extend it rather than replace it, preserving the discipline and architecture-first intent that define CareerOS development.

Future sections may include:

- Coding Standards
- Testing Strategy
- Release Process
- Branching Strategy Evolution
- Security Guidelines
- AI Development Guidelines
- Code Review Standards

This handbook is a living engineering document. Future engineering practices should extend this handbook rather than replace it.

## Definition of Done

A milestone is considered complete only when all applicable conditions are satisfied.

- ✓ Architecture documented
- ✓ ADRs created or updated (when required)
- ✓ Implementation completed
- ✓ Automated tests passing
- ✓ Documentation updated
- ✓ Code review completed
- ✓ Repository clean
- ✓ Project state checkpoint updated in `docs/project-state/`
- ✓ Commit pushed
- ✓ Annotated Git tag created (major milestones)
- ✓ GitHub Release published (platform checkpoints)
- ✓ Next milestone prepared

Not every milestone requires a tag or GitHub Release, but every major platform checkpoint does.
