# M2 Claim Lifecycle — Draft → Generated → Reviewed → Approved → Deprecated → Archived

## Status

Proposal — architecture only. No implementation.

## States

| State | Meaning |
|---|---|
| `draft` | Human-authored starting point; not yet in any document |
| `generated` | Proposed by a machine (LLM, extractor, import, reasoning engine); not yet human-reviewed |
| `reviewed` | A human has examined the claim; pending approval decision |
| `approved` | Accepted; eligible for use in target contexts and documents |
| `deprecated` | No longer actively used (superseded, evidence withdrawn, or owner retired it); retained |
| `archived` | Retired from all selection; retained for auditability |

## State Diagram

```
                ┌─────────────┐
   human writes │   draft     │
                └─────┬───────┘
                      │ review requested
                      ▼
                ┌─────────────┐    approve    ┌─────────────┐
   machine      │  generated  │───(reviewer)──▶│  approved   │
   proposes ────▶            │                └──────┬──────┘
                └─────┬───────┘                      │ deprecate
                      │                              ▼
                      │ review requested       ┌─────────────┐
                      ▼                        │ deprecated  │
                ┌─────────────┐                └──────┬──────┘
                │  reviewed   │                       │ archive
                └─────┬───────┘                       ▼
                      │ reject / request changes  ┌─────────────┐
                      ▼                           │  archived   │
                ┌─────────────┐                   └─────────────┘
                │  (→ draft)  │
                └─────────────┘
```

A claim may also be archived directly from `approved` or `deprecated`.

## Who or What Moves a Claim

| Actor | Role | Transitions allowed |
|---|---|---|
| **Professional (owner)** | The human the claim is about | draft → reviewed; draft → approved (self-approval permitted); generated → draft (to edit a machine proposal); approved → deprecated; deprecated → archived |
| **Reviewer (human)** | Designated reviewer/verifier | generated → reviewed; reviewed → approved; reviewed → draft (request changes); approved → deprecated (with reason) |
| **LLM / extractor / import (machine)** | Proposes claims from profiles, documents, or evidence | *(creates)* → generated |
| **Reasoning Engine (deterministic)** | Flags claims for review or deprecation | approved → deprecated (when supporting evidence is withdrawn — auto-flag, human confirms); generated → reviewed (batch review requests) |
| **Administrator** | System-level governance | any → archived; deprecated → approved (restore) |

### Guardrails

1. **`generated` never enters a document.** Only `approved` (or, with explicit
   reasoning-layer override, `reviewed`) claims are selectable for output.
2. **Deprecation from evidence withdrawal is flag-then-confirm.** The reasoning
   engine marks a claim `pending`-style for deprecation when its evidence is
   archived or downgraded to `estimated`; a human confirms the transition. No
   silent removal from documents.
3. **History is append-only.** Every transition records `{ at, from, to, actor,
   reason }` (see YAML in 05-schema-proposal).
4. **Rejection is reversible.** `reviewed → draft` lets the owner revise and
   resubmit. Nothing is destroyed; `archived` is a retention state, not a delete.

## Claim Proposals by Source

| Source | Entry state | Typical path |
|---|---|---|
| Human professional | draft | draft → reviewed → approved |
| LLM suggestion (from profile/evidence) | generated | generated → reviewed → approved (or → draft for editing) |
| Resume/import extractor | generated | same as LLM |
| Evidence upgrade (e.g. metric verified) | promoted from generated | generated → approved (reasoning engine auto-promotes only with evidence `verified`) |
| Reasoning engine finding | generated | generated → reviewed → approved |

## Example Lifecycle (worked trace)

1. **generated** — LLM proposes: *"I reduced deployment time by 60%."*
   (candidate for the Kubernetes platform claim) — `produced_by: llm:proposer`.
2. **reviewed** — owner requests review; reviewer reads supporting evidence
   (`metric` churn data + deployment log).
3. **approved** — reviewer approves; claim becomes eligible for `cv`,
   `linkedin`, `biography`, `interview_answers`, `technical_profile`.
4. **used** — the CV and LinkedIn sections select the claim.
5. **deprecated** — the reasoning engine detects the deployment evidence is
   archived (metric no longer tracked) → flags → owner confirms deprecation.
6. **archived** — after retention, administrator archives; the full transition
   history remains for auditability.
