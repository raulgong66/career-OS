# Evidence Pipeline Hydration

Status: implemented and verified (2026-08-15).
Relates to the deterministic reasoning/optimization layers. This document records
what was actually implemented and verified so that the milestone can be understood
without the original design conversation.

## Why evidence hydration was implemented

The canonical profile schema already supported a top-level `evidence` collection,
but profile acquisition never populated it. Real profiles produced before this
milestone carried:

- an empty top-level `profile["evidence"]` collection, and
- the substantiating data embedded elsewhere: `skill.extensions.experienceEvidence`
  (skill-to-experience links) and `extensions._acquisition` (source-document
  provenance trace).

Consequences of the gap:

- The optimizer could not attach evidence to recommendations — it produced
  recommendations with no source, strength, provenance, or rationale.
- The reasoning layer computed skill-evidence strength but reported a hardcoded
  confidence of `1.0`, so a profile with zero documented experience substantiation
  looked identical to one with strong, verified substantiation.
- Nothing made provenance visible, so unverifiable claims could be presented with
  the same confidence as verified claims.

This milestone hydrates `profile["evidence"]` from data already in the profile
(deterministic, idempotent, never fabricated) and derives reasoning confidence from
that evidence instead of a constant.

## What changed

- New module `careeros/evidence_hydration.py` — the single source of the evidence
  strength, provenance, cap, combined-grade, and item-building logic. Both the
  reasoning rule and the optimizer reuse it (no duplicated confidence math).
- `careeros/acquisition/profile_builder.py::build` — populates `profile["evidence"]`
  at the end of `build()`.
- `careeros/optimizer.py` — `CVOptimizer.__init__` calls `_hydrate_evidence()`: it
  fills `profile["evidence"]` only when the collection is empty AND skills carry
  `experienceEvidence`; otherwise the profile is left untouched. Existing evidence
  is never overwritten.
- `careeros/reasoning/rules/skill_rules.py` — `SkillEvidenceStrengthRule` now derives
  `ReasoningResult.confidence` from evidence (mean evidence strength) instead of
  returning `1.0`, and adds provenance metadata. Other rule families are unchanged.
- Tests: `tests/test_evidence_hydration.py` (new), `tests/test_skill_rules.py`
  (evidence-confidence assertions), plus coverage through `test_profile_builder.py`,
  `test_acquisition_integration.py`, and `test_api.py`.

## Files changed (this milestone)

- `careeros/evidence_hydration.py` (new)
- `careeros/acquisition/profile_builder.py`
- `careeros/optimizer.py`
- `careeros/reasoning/rules/skill_rules.py`
- `tests/test_evidence_hydration.py` (new)
- `tests/test_skill_rules.py`
- `docs/architecture/evidence-hydration.md` (this document)

## Canonical evidence model: (skill, experienceEvidence)

The canonical evidence item is a schema-shaped record produced from one
`skill.extensions.experienceEvidence` entry:

- One item per unique `(skillId, experienceId)` pair (deduplicated by
  `evidence-<skillId>-<experienceId>`).
- Deterministic: skills iterated in profile order, each skill's evidence entries in
  order. Idempotent: computed purely from the profile's skills; pre-existing
  evidence is never read or duplicated.
- Item shape (`schemas/profile.schema.json`, `$defs/evidence`):
  `{ id, title, description, evidenceType: "experience", relatedRefs: [skill,
  experience], extensions }`. `extensions` carries `skillId`, `skillName`,
  `experienceId`, `experienceTitle`, `organization`, `evidenceStrength`,
  `evidenceStrengthLabel`, `provenance`, `provenanceExplanation`,
  `confidenceGrade`, `basis`.
- No source name, hash, or import timestamp is ever fabricated. `relatedRefs` and
  `extensions` reference only entities that actually exist in the profile.

Verified on the real Smith staging profile: 48 raw `experienceEvidence` entries
hydrate into 24 evidence items (one per unique skill–experience pair) for 12
evidence-bearing skills.

## Evidence-strength semantics

Evidence strength is a deterministic float in `[0.1, 1.0]` computed by
`compute_evidence_strength` from three collected facts per skill — experience
count, distinct organization count, and total years of use — with the same math the
skill-evidence reasoning rule has always used. There is no new confidence formula;
the previous milestone only moved the existing formula into the shared module and
started deriving the reasoning confidence from it.

Examples (verified):

- 3 experiences / 3 organizations / 7.12 years → `0.85` → label `very_high` (Kali
  Linux on Smith).
- 2 experiences / 2 organizations / 7.12 years → `0.75` → label `high` (Burp Suite,
  Gobuster, Hydra, ... on Smith).
- 1 experience / 1 organization / 10.29 years → `0.55` → label `medium` (Python).
- No experience evidence → `0.15` → label `very_low` (floor; unsubstantiated skill).

Band labels: `very_low` (>= 0.2), `low` (>= 0.4), `medium` (>= 0.6), `high`
(>= 0.8), else `very_low`/`very_high` at the extremes.

## Provenance-grade and cap model

Provenance is classified from `extensions._acquisition`, using only fields that are
actually present (nothing is inferred or invented):

- `full` — `sourceHash`, `sourceName`, and `importedAt` are all present.
- `partial` — an acquisition trace exists but at least one of the three is missing.
- `none` — no acquisition trace.

The combined `confidenceGrade` caps evidence strength by provenance:

- `full` permits up to `very_high`.
- `partial` permits up to `high`.
- `none` permits up to `medium`.

The grade is the strength label lowered to the provenance cap; it never exceeds
either. The two axes remain independently visible on every item:
`evidenceStrengthLabel` (strength) and `provenance`/`provenanceExplanation`
(source), alongside the combined `confidenceGrade`.

Verified: Kali Linux on Smith is strength `very_high` (0.85), provenance `partial`,
grade `high`. No evidence item on any real staging profile contains a `sourceHash`,
`sourceName`, or `importedAt` key — provenance is never fabricated.

## Difference between evidence confidence and reasoning confidence

Two distinct confidence notions exist and are intentionally kept separate in the
output:

1. **Evidence-derived confidence** — per claim (per evidence item / per skill).
   Carried on each evidence item as `evidenceStrength` + `evidenceStrengthLabel` +
   `confidenceGrade` (+ `provenance`), and per skill inside the
   `skill_evidence_strength` finding's `value` (`confidence` + `label` per skill).
   Semantics: how well a specific skill claim is substantiated by experience
   evidence, modulated by source provenance.
2. **Reasoning-finding confidence** — per finding (`ReasoningResult.confidence`),
   the finding's overall confidence. For deterministic rules it remains `1.0`
   (computed facts from the profile). For the evidence rule it is the mean evidence
   strength across analyzed skills (for Smith: `0.57`).

In the reasoning-finding output the evidence-derived quantities are named with an
`evidence_` prefix (`evidence_strength_mean`, `evidence_confidence_grade`) or
`provenance`, so they cannot be mistaken for the finding's own `confidence` field.

Consequence (verified): the Smith reasoning distribution is
`{"0.57": 1, "1.0": 33}`. Exactly one finding — `skill_evidence_strength` — has
evidence-derived confidence because it is the only evidence-bearing rule and the
engine emits one finding per rule; its `value` carries the differentiated per-skill
confidence for all skills (Kali 0.85, 10 skills 0.75, Python 0.55, 5 unsubstantiated
skills 0.15). This is the designed aggregation granularity, not a wiring defect: the
24 evidence items substantiate 12 distinct skill claims, and per-claim confidence is
visible at the evidence-item and optimizer level.

## Alternatives considered / rejected

- **Emitting one reasoning finding per skill.** Rejected: changes the reasoning
  engine's finding cardinality and would break the report/contract structure. The
  engine produces one finding per rule; per-skill detail belongs in the finding's
  `value` and in the evidence items.
- **Fabricating or inferring provenance from file names / timestamps.** Rejected:
  provenance must record only what is actually on record; inference would mislabel
  unverifiable sources.
- **Reweighting the optimizer's `evidence_strength` scoring term.** Rejected: out of
  scope. The optimizer already scores `evidence_strength`; this milestone only makes
  the evidence data it consumes real.
- **New LLM-based confidence.** Rejected: confidence must stay deterministic and
  auditable; no LLM involvement.

## Verification and test results

- Focused (evidence hydration + skill rules + profile builder + acquisition
  integration + API): **247 passed**.
- Regression (reconciliation, import classification, CLI, profile quality,
  knowledge graph, experience/recommendation/tenure rules, reasoning): **436
  passed**.
- Full backend suite: **1322 passed**, 1 pre-existing Starlette/httpx deprecation
  warning, ~45s.
- Mandatory acceptance tests covered: strong evidence + partial provenance caps to
  `high`; strong evidence + no provenance caps to `medium`; full provenance not
  capped; thin/no evidence produces no manufactured items and never a `high` grade;
  deterministic + idempotent + schema-valid; optimizer consumes hydrated staging
  evidence; genuinely empty profiles retain `already_complete` semantics.
- Real-profile verification: Smith 24 items, reasoning mean 0.57 (provenance
  `partial`, grade `medium`), Kali item `very_high`/`partial`/`high` with
  plain-language basis; no fabricated provenance anywhere.

## Scope and explicit non-goals

In scope: evidence hydration, evidence-derived confidence for the evidence rule,
provenance capping, plain-language basis text, documentation.

Explicit non-goals (unchanged): team optimization, proposal generation, RFP parsing,
automated ingestion, UI redesign, external integrations, reconciliation mutation
(merge/promote/archive/delete), and any change to the evidence-strength scoring
formula.

## Known limitations

- **Missing provenance in current real profiles.** All real staging profiles were
  imported before source metadata was recorded, so their `_acquisition` traces lack
  `sourceHash` (and often `sourceName`/`importedAt`). Their provenance is therefore
  `partial` at best and their grades are capped at `high`. Full provenance will only
  appear once source documents are re-imported through the acquisition pipeline with
  source metadata; until then, unverified sources are honestly reflected in grades.
- The reasoning finding confidence is a mean over all analyzed skills, including
  unsubstantiated skills at the floor (0.15). This is intentional and transparent
  (`total_skills_analyzed` and per-skill values are exposed), but a profile with many
  unsupported skills will report a lower aggregate than one where every skill is
  substantiated.
- Evidence strength and grade are floats/labels derived from experience breadth and
  depth only; they do not account for the recency or seniority of the experiences.
