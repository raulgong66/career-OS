# M2 Open Questions — The Professional Claim Model

## Status

Unresolved architectural questions. Deliberately open; each is resolvable at the
start of its owning workstream. None are silently decided in code (R10.1).

## Authoring & Editing

**Q1. Should claims be manually editable?** May a professional edit an
`approved` claim directly (creating a new version), or must changes go through
review again? If versioned, how are prior versions kept? (Owner: M4/authoring)

**Q2. Should LLMs propose claims?** The lifecycle permits `generated` claims
from LLMs. Should proposals be batched, rate-limited, and gated behind explicit
review, or is auto-`generated` into `draft` acceptable? (Owner: M4)

**Q3. Claim provenance of wording.** When an LLM generates a claim, is the
generated wording itself treated as internal metadata (never shown verbatim) or
as reviewable text the owner may adopt verbatim? (Owner: M4)

## Expiry & Recency

**Q4. Can claims expire?** Quantified claims (e.g. "reduced churn 30%") age.
Should the model carry an expiry/recency window, or does recency live entirely
in evidence `provenance.capturedAt` (ADR-002)? (Owner: M3)

**Q5. Recency vs. relevance.** A dated achievement remains true but may become
irrelevant. Is that a `deprecated` event, a recency signal on selection, or a
new concept (freshness) distinct from confidence? (Owner: M3)

## Reuse & Context

**Q6. Can multiple target contexts reuse identical claims?** The model says yes
via `targetContexts`. Must a claim be *word-for-word identical* across contexts,
or may context variants (tone/length) exist as derived renderings of one claim?
(Owner: M4 / workstream F)

**Q7. Context-specific ordering.** `priority` is per-claim, but relative
ordering within a context likely needs per-context weighting. Should ordering be
a claim attribute, a context attribute, or a reasoning-engine decision? (Owner:
M3)

## Feedback & External Input

**Q8. Can recruiters provide feedback on claims?** If a recruiter flags a claim
as overstated, where does that land — a claim-level signal, an evidence-level
signal, or a separate feedback entity? Does it require human review before
affecting selection? (Owner: M3/M4)

**Q9. Who counts as "reviewer"?** Is review a role distinct from the
professional and administrators, and can the professional self-approve
`draft → approved`? (Owner: M4)

## Language & Localization

**Q10. Should claims support localization?** `statement` is a single string.
Should the model support per-locale statement variants, or is localization a
rendering concern that translates from a canonical-language claim? (Owner:
workstream F, out of current scope)

## Structure & Identity

**Q11. Claim granularity.** Can one claim reasonably be decomposed (e.g. the
Kubernetes build claim into platform design + security + automation)? Is there a
claim hierarchy (parent/child), and does deduplication need claim identity
rules analogous to ADR-002's canonical identity? (Owner: M4)

**Q12. Claim ↔ element duplication.** A claim often restates experience
summary text. Is the claim the *source of truth* for document text going
forward (with experience summaries derived from claims), or do they coexist?
(Owner: workstream F)

**Q13. Conflict between claim and evidence.** If a claim asserts an outcome the
evidence contradicts (or evidence is `estimated`), is that a `pending` claim
state, a reasoning-flag, or a separate inconsistency finding? (Owner: M3)

**Q14. Strength ladder mapping.** `weak | supported | strong | exceptional`
needs an eventual mapping from the derivation inputs (03-domain-model). Is that
mapping per-industry or global? (Owner: M3)

**Q15. Visibility semantics.** `public | private | internal` — does `private`
mean "visible only to the owner" and `internal` "visible to reasoning but never
to recruiters"? Clarify the privacy boundary with ADR-002's render rules.
(Owner: security / F)
