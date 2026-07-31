# CareerOS Platform Beta

Platform Beta is the evolution of CareerOS from an AI document generation platform into a **Professional Knowledge Platform** - a system for the continuous acquisition, reasoning, evolution, and intelligent management of professional knowledge.

## Scope

Platform Alpha delivered the stable baseline:

- Canonical Professional Profile as the single source of truth
- Deterministic reasoning engine
- Markdown and DOCX document generation
- Tailored CV and Interest Letter generation
- Runtime configuration subsystem (`.env`) with local LLM (Ollama) integration
- Automated tailoring workflow with optimization metrics

Platform Beta builds on this baseline. It does not replace it.

## Documents

| Document | Purpose |
|---|---|
| [Vision.md](Vision.md) | Platform Beta vision and strategic direction |
| [Roadmap.md](Roadmap.md) | Major workstreams for Platform Beta |
| [Milestones.md](Milestones.md) | Planning milestones (M1-M5) |
| [README.md](README.md) | This index and architecture principles |

## Architecture Principles

The following principles guide all Platform Beta work:

1. **Canonical Professional Profile remains the single source of truth.** Every artifact, analysis, and recommendation derives from the canonical profile. Nothing appears in an artifact that is not represented in the profile.
2. **Deterministic reasoning remains the primary decision engine.** Analytical facts are computed deterministically before any LLM interaction. LLMs assist but never replace deterministic reasoning.
3. **LLMs assist but never replace deterministic reasoning.** LLM output is advisory, reviewed, and always subject to deterministic validation.
4. **Evidence always outweighs assumptions.** Recommendations and generated content must be traceable to evidence. Assumptions are never presented as facts.
5. **Recruiter-facing documents never expose internal metadata.** Tailored documents remain clean of internal identifiers, reasoning artifacts, and derivation details.
6. **Every feature must strengthen the Professional Knowledge Platform vision.** Features that fragment knowledge, weaken the canonical profile, or erode determinism are out of scope.

## Relationship to Platform Alpha

Platform Alpha is frozen as the stable baseline (tag `v1.0.0-platform-alpha`). Platform Beta development proceeds on this branch (`feature/platform-beta`) without modifying Platform Alpha behavior or production code until a feature is explicitly approved.

## Working Agreement

- No production code changes on this branch outside of approved Platform Beta planning and enablement work.
- Milestones M1-M5 are planning milestones, not commitments.
- Each workstream is decomposed into concrete implementation tasks when work begins.
