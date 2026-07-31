# M1 Open Questions — The Professional Evidence Model

## Status

Unresolved design questions. These are deliberately left open to avoid blocking
the architecture; each is resolvable at the start of its owning workstream.

## Identity & Deduplication

**Q1. Canonical identity definition.** The proposal derives canonical identity
from `kind + normalized(title) + source + date(window)`. What is the exact
normalization (case, punctuation, synonyms, language) and how wide is the date
window? (Owner: M2 Knowledge Acquisition)

**Q2. Content fingerprinting.** Should identity be augmented with a content
fingerprint (hash of normalized text + metrics)? This improves dedup but
complicates merge when prose is lightly edited. (Owner: M2)

**Q3. Cross-source duplicates.** A metric confirmed both by a resume and by a
registry produces two evidence items with different provenance. Are they
`duplicate_evidence`, or the *same* evidence with multiple provenance records?
(Owner: M2)

## Confidence

**Q4. Provenance reliability scale.** The model stores `source.kind`
(document/url/person/system/model) as a reliability input but no ordering.
Should the model assert an ordering (e.g. system > person > document) even
without scoring? (Owner: M3)

**Q5. Confidence aggregation.** When an element is supported by multiple
evidence items with mixed statuses, the model stores inputs only. Is the
aggregate a derived, per-element concept defined in M3, or should it be
per-artifact-section? (Owner: M3)

## Relationships

**Q6. Bidirectional consistency enforcement.** The proposal says element →
evidence is authoritative and `relatedRefs` is derived. Should derivation be a
build-time index, a runtime validation, or both? Affects the validator and the
graph. (Owner: platform core)

**Q7. Summary- and claim-level granularity.** `professionalSummary` and
`careerClaims` are elements like any other. Do sub-claims within a summary text
need their own evidence refs, or is element-level refs sufficient? (Owner: M1
follow-up or M4)

**Q8. Skill evidence semantics.** When evidence supports a skill (e.g. a GitHub
repo backing "Kubernetes advanced"), does that assert *possession* of the skill,
*demonstration* of it, or both? This affects how the Reasoning Layer may use it.
(Owner: M3)

## Measurable Outcomes

**Q9. Metric period vs. evidence date.** A metric has its own `period`, while
evidence has `provenance.capturedAt`. When an element spans the period but the
evidence was captured later (e.g. annual review in February for the prior year),
which date governs recency? (Owner: M3)

**Q10. Unit normalization.** `unit` is free text ("percent", "%", "pct"). Does
the model need a unit vocabulary, or does normalization live in the scoring
layer? (Owner: M3)

## Acquisition

**Q11. Merge conflict representation.** When merged evidence conflicts, the
proposal preserves both variants with a `pending_review` marker. Is a conflict a
state on one evidence item, or a pair of linked items? (Owner: M2)

**Q12. Import attribution for re-verified evidence.** A `verified` item
originally `imported` — does `history` record the full chain, and does the model
need a separate `verificationChain` for auditability? (Owner: M2)

## Privacy & Traceability

**Q13. Private links.** Evidence links may point to internal resources (e.g.
`metrics.acme.internal` in the example). Does the model mark link visibility so
artifacts never leak internal URLs, or is the render layer solely responsible?
(Owner: F / security)

**Q14. Evidence sharing across profiles.** If a future multi-profile feature
exists, is evidence per-profile or shared? The proposal assumes per-profile.
(Owner: platform core, out of current scope)

## Reasoning & Explainability

**Q15. Rule-to-evidence coupling.** ADR 0005 lets rules reference "supporting
graph nodes." Should findings reference evidence ids directly, or via the
element that holds them? Direct ids are more precise but couple rules to the
evidence model. (Owner: M3, with this model as input)
