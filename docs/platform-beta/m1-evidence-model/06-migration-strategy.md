# M1 Migration Strategy — Additive, Backward Compatible

## Status

Proposal — architecture only. No implementation.

## Constraint

Migration must be **additive and backward compatible**. No breaking changes to
existing profiles, the schema validator, artifact generation, the optimizer, or
AI providers. Platform Alpha behavior is preserved byte-for-byte for unchanged
profiles.

## Principle: Superset Compatibility

The current `schemas/profile.schema.json` `evidence` definition is:

```jsonc
// today — required: ["id"], all other fields optional
{
  "id": "…", "title": "…", "description": "…",
  "evidenceType": "…", "links": [], "relatedRefs": [], "extensions": {}
}
```

The proposed model (04) is a **strict superset**:

| Today | Proposal | Relationship |
|---|---|---|
| `id` | `id` | unchanged |
| `title` | `title` | unchanged |
| `description` | `summary` | `description` accepted as an alias in the transition period |
| `evidenceType` | `kind` | free text → enum; `evidenceType` values are mapped onto the nearest `kind` |
| `links` | `links` | unchanged |
| `relatedRefs` | `relatedRefs` | unchanged shape; `type` set grows |
| — | `provenance`, `verificationStatus`, `reviewState`, `metrics`, `history` | added; **all optional** with defaults |

Because every new field is optional and every existing field keeps its name,
semantics, and nullability, **any profile that validates today validates after
migration**.

## Migration Phases

### Phase 0 — Do nothing (today)

No schema change, no tooling. Baseline captured: all existing profiles and
tests validate against the current schema.

### Phase 1 — Additive schema extension

- Add the new optional fields to the `evidence` definition per the proposal.
- Keep `required: ["id"]`. Do not re-require any new field.
- Add the new `evidence` kinds and status enums as *open* enums (allow
  `evidenceType` values to pass through) so existing documents never fail on
  previously-valid values.
- Result: current profile corpus validates unchanged; new fields are accepted.

**No data rewrite. No migration job. No validator change.**

### Phase 2 — Optional enrichment (separate effort, not required)

- A dedicated, off-path tool imports legacy profiles and creates evidence items
  with `verificationStatus: generated` (later promoted by user/verifier).
- Enrichment never modifies an element's claims; it only *adds* evidence and
  `evidenceRefs`.
- This is explicitly **not** a migration requirement (R9.3) and ships only when
  a Beta workstream needs it.

### Phase 3 — Deprecation (far future, only after Beta features rely on the model)

- `evidenceType` and `description` aliases marked deprecated; documents still
  validate. Removal would require its own ADR.

## Compatibility Guarantees

| Consumer | Guarantee |
|---|---|
| Schema validator | never rejects a profile it previously accepted |
| Optimizer (`_get_backing_evidence` path) | reads the same `evidenceRefs`/`relatedRefs` shapes; behavior unchanged |
| Artifact generation / AI providers | consume element text and `sourceRef`s only; unaffected |
| Reasoning Layer (future) | reads the new fields; purely additive consumer |
| Knowledge Graph (future, ADR 0005) | graph nodes derive from elements; evidence becomes first-class nodes |

## What Never Happens in Migration

- No in-place rewriting of existing evidence items.
- No removal or renaming of existing fields.
- No change to `required` constraints.
- No new required dependencies (e.g. evidence is never required for an element).
- No changes to recruiter-facing output.

## Backward-Compatibility Rules for the Proposal Itself

1. Every new field has a default so an old profile parsed by the new model has
   well-defined values: `verificationStatus: generated`, `reviewState: draft`,
   `provenance: null`, `metrics: []`, `history: []`.
2. `description` maps to `summary` at the model boundary; `evidenceType` maps
   to `kind` with a fallback to `document` for unknown values.
3. Refs remain `{ id, type }`; the reference model gains types, never loses
   them.

## Verification

After Phase 1, run the existing schema-validation suite over the current corpus
and confirm zero regressions. The suite is a precondition for any Phase 2 work.
