# ADR 004: Core Platform Boundaries

## Status

Accepted

## Context

CareerOS Platform Beta is evolving from a single AI document-generation product (Platform Alpha, tag `v1.0.0-platform-alpha`) into a **Professional Knowledge Platform**. The roadmap defines future modules: Interview Preparation, Career Analytics, Learning Planner, Application Tracking, and Skill Gap Analysis. All of them must share the same canonical profile, knowledge graph, reasoning, and artifact lifecycle.

Today the boundary between the shared foundation and the AI Tailoring module is implicit. Several indicators:

- The `careeros` package mixes module-neutral services (schema, validation, knowledge, reasoning) with tailoring concepts (job-description optimization, optimization metrics, recommendation application).
- The API layer `api/main.py` contained the entire resolution/artifact-lifecycle policy inline, so any future module that edits the profile would have to duplicate or re-implement it.
- Private symbols leak across module boundaries (`markdown_cover_letter.py` called `CVOptimizer._extract_requirements`; `api/main.py` imported `_is_measurable` from a rules module).
- The shared generation pipeline (`careeros/pipelines.py`) imports the tailoring optimizer.

Without an explicit boundary, each new module either re-implements Core behavior or acquires accidental couplings to AI Tailoring — exactly the failure mode the Platform Beta principles (canonical profile as single source of truth; deterministic reasoning first; evidence over assumptions) are meant to prevent.

## Decision

Establish an explicit **Core / Module / App** boundary:

1. **Core** (`careeros/`) is the deterministic, module-neutral foundation: canonical profile schema and validation, profile loading/repository, acquisition, knowledge graph, reasoning engine and rule registry, export contract and evidence selection, generation pipeline, and the **Resolution Engine**. Core never imports module concepts and never talks to AI providers directly except through provider abstractions.

2. **Modules** (AI Tailoring today; the five future capabilities tomorrow) consume Core only and never depend on each other. Module concepts — job descriptions, optimization metrics, interview question banks, skill targets — stay inside the module.

3. **Apps** (`api/`, `careeros_cli/`, `frontend/`) are the only place transports, configuration, and module composition live. They translate Core/module errors into their own error surface.

4. **The Resolution Engine is Core.** Deterministic, guided edits to the canonical profile and the artifact lifecycle (marking affected generated artifacts `stale`; regeneration is always an explicit user action) are platform policy. This milestone extracts it from the API into `careeros/resolution.py`, exposed through the public `careeros` facade (`apply_resolution`, `RESOLVABLE_RULES`, typed exceptions such as `ResolutionTargetNotFoundError`, `InvalidAchievementError`, `AchievementNotMeasurableError`, `UnsupportedRuleError`). It is transport-free; the API maps its exceptions to HTTP responses.

5. **Cross-boundary access goes through public APIs only.** As part of this milestone: `markdown_cover_letter.py` uses the new public `CVOptimizer.extract_requirements` instead of the private `_extract_requirements`, and the app no longer imports `_is_measurable` from a rules module.

6. **New modules land behind this boundary.** Until a module is approved, module code may remain inside `careeros/` (as AI Tailoring does today) but must follow the dependency rule and be documented in `docs/architecture/09-core-vs-modules.md`.

## Consequences

**Positive:**

- **Reusable foundation.** Interview Preparation, Career Analytics, Learning Planner, Application Tracking, and Skill Gap Analysis all start from the same Core instead of forking profile-editing or artifact-lifecycle logic.
- **Profile integrity.** Because resolution and validation live in Core, no module writes the canonical profile directly, preserving the single-source-of-truth guarantee.
- **Testability.** The Resolution Engine is unit-testable without HTTP; the API layer becomes a thin error-mapping shim. All 620 backend tests pass unchanged.
- **Clearer evolution path.** Tailoring-heavy code (`optimizer.py`, `recommendation_applier.py`, `docx_renderer.py`, cover-letter generators, `generate_tailored_artifact`) can migrate into a dedicated module without touching Core consumers.

**Negative:**

- **Some tailoring code still lives in Core.** `careeros/pipelines.py` still exports `generate_tailored_artifact` and imports the optimizer; `markdown_cv.py` still embeds LLM calls. Moving these behind shims is deferred to keep this milestone small and safe.
- **Boundary discipline requires maintenance.** New code can silently blur the boundary; the architecture doc and code review must enforce the dependency rule.

**Future considerations:**

- Extract `generate_tailored_artifact` into a tailoring module behind a re-export shim (`from careeros import generate_tailored_artifact` must keep working).
- Introduce an AI provider interface for the LLM calls in generators and acquisition.
- Move cover-letter generators into the tailoring module.
- Harden the reasoning layer against `KnowledgeGraph` with an abstract interface.
