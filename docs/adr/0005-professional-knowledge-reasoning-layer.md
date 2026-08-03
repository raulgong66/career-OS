# ADR 0005: Professional Knowledge Reasoning Layer

## Status

Accepted

## Context

The current CareerOS architecture ends at the Knowledge Graph (M5). AI providers
currently read the raw canonical profile or graph directly when generating
artifacts (CV, cover letter, portfolio). This design has several shortcomings:

- **Prompt coupling.** Each AI provider must re-implement the same analytical
  logic (find strongest experience, compute tenure, identify leadership roles)
  inside its prompt. Changing the analysis requires updating every prompt.
- **Non-determinism.** The same profile can produce different analyses depending
  on prompt phrasing, model version, or temperature settings.
- **Untestable.** Analytical logic embedded in prompts cannot be unit tested.
- **Provider lock-in.** Analytical patterns that work for one provider may not
  transfer to another. Switching providers requires re-engineering the analysis.
- **Token waste.** Every provider re-processes the full profile to derive the
  same basic facts.

There is no existing layer that performs deterministic professional knowledge
analysis before the AI provider. The Knowledge Graph provides navigable
structure but no analytical rules.

## Decision

Introduce a **Professional Knowledge Reasoning Layer** with the following
design constraints:

1. **Reasoning is separated from AI.** The reasoning layer is a pure,
   deterministic library that operates on the Knowledge Graph. It has no
   dependency on any AI provider.

2. **Deterministic rules are preferred over prompt-only reasoning.**
   Every analytical operation that can be expressed as a pure function over
   the graph is implemented as a Rule. Rules produce Findings. Findings are
   composed into an Evidence Package.

3. **The Evidence Package is the contract.** AI providers never read the raw
   profile or graph. They receive a structured Evidence Package containing
   pre-computed findings, evidence sets, strengths, weaknesses, gaps, and
   recommendations. The AI's sole responsibility is to convert structured
   evidence into natural language.

4. **Rules are composable and extensible.** Rules implement a common interface
   and are registered in a Rule Registry. New rules can be added without
   modifying existing rules or AI prompts.

5. **Multiple AI providers are supported without duplication.** The same
   Evidence Package is consumed by any provider. Providers differ only in
   their generation capability, never in their analytical foundation.

## Consequences

**Positive:**

- **Explainability.** Every Finding in the Evidence Package traces back to a
  specific Rule and its supporting graph nodes. Users can ask "why was this
  experience selected?" and receive a deterministic answer.
- **Testability.** Rules are pure functions. They accept a Knowledge Graph and
  return Findings. Unit tests cover edge cases, regressions, and combinations
  without invoking any AI.
- **Provider independence.** The same Evidence Package feeds OpenAI, Anthropic,
  local models, or future providers. Provider switching requires no analytical
  rework.
- **Token efficiency.** The Evidence Package is a fraction of the raw profile
  size. AI providers spend tokens on generation, not analysis.
- **Prompt simplification.** AI prompts become formatting instructions for
  pre-analysed data. No analytical logic lives in prompts.
- **Caching.** The Evidence Package can be cached and re-used until the
  underlying profile changes. Re-generation of the same artifact type does not
  re-run analysis.
- **Auditability.** Every generated artifact includes an evidence trail back to
  the Reasoning Layer and ultimately to source documents.

**Negative:**

- **Additional layer to maintain.** The Reasoning Layer adds code, tests, and
  documentation beyond the existing pipeline.
- **Rule maintenance overhead.** Rules must be kept current with evolving
  professional knowledge patterns. Outdated rules produce stale findings.
- **Upfront design cost.** The Rule interface, Rule Registry, and Evidence
  Package schema must be designed correctly before implementation begins.

**Future considerations:**

- Rules can be versioned independently of AI prompts, enabling A/B testing of
  analytical strategies.
- The Evidence Package schema evolves separately from the canonical profile
  schema, decoupling acquisition from reasoning.
- Custom rules (per-organization, per-industry) can be injected without
  modifying core rules.
