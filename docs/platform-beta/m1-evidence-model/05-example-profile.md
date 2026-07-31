# M1 Example Profile — A Worked Canonical Profile with Evidence

## Status

Illustrative example. Not an implementation, not a fixture.

## Setup

A fictional professional, **Mara Chen**, Senior Platform Engineer. The profile
shows how evidence is attached to elements, how the traceability path is
exercised, and how confidence states are represented. It deliberately includes:

- evidence supporting multiple elements (many-to-many),
- imported evidence (from a resume),
- verified evidence (a certification registry),
- measured outcomes,
- an unused evidence item,
- a career claim (future element) referencing evidence.

## Canonical Profile (excerpts)

```yaml
profileVersion: "2.0"
schemaVersion: "1.1"

professional:
  id: "prof_marachen"
  name: "Mara Chen"
  title: "Senior Platform Engineer"

professionalSummary:
  text: "Senior platform engineer focused on reliability and developer velocity."
  evidenceRefs:
    - id: "ev_2025-003"
      type: "evidence"
      note: "bulk of summary claims trace to the 2025 annual review."

experience:
  - id: "exp_201"
    org: "Acme Cloud"
    role: "Senior Platform Engineer"
    start: "2023-02-01"
    end: null
    summary: "Led reliability engineering for a multi-tenant control plane."
    evidenceRefs:
      - id: "ev_2025-001"
        type: "evidence"
      - id: "ev_2025-002"
        type: "evidence"

  - id: "exp_200"
    org: "Beta Systems"
    role: "Backend Engineer"
    start: "2020-06-01"
    end: "2023-01-31"
    summary: "Built payment processing services at high transaction volume."
    evidenceRefs:
      - id: "ev_2025-004"
        type: "evidence"

skills:
  - id: "skl_310"
    name: "Kubernetes"
    level: "advanced"
    evidenceRefs:
      - id: "ev_2025-002"
        type: "evidence"

certifications:
  - id: "cer_500"
    name: "Certified Kubernetes Administrator"
    issuer: "CNCF"
    credentialId: "CKA-2024-88421"
    evidenceRefs:
      - id: "ev_2025-005"
        type: "evidence"

careerClaims:                    # proposed future element
  - id: "claim_003"
    statement: "Reduced customer churn by ~30% at Acme."
    kind: quantified_outcome
    date: "2025-03-31"
    evidenceRefs:
      - id: "ev_2025-001"
        type: "evidence"

evidence:
  - id: "ev_2025-001"            # SUPPORTS exp_201 + claim_003  (many-to-many)
    kind: metric
    title: "Customer churn reduction at Acme"
    summary: "Reduced monthly churn from 4.8% to 3.2% over six months."
    provenance:
      source: { kind: document, id: "doc_resume_2025-04", label: "Resume submitted 2025-04" }
      capturedAt: "2025-04-15T10:00:00Z"
      capturedBy: "importer:resume-v2"
    verificationStatus: imported
    reviewState: pending_review
    metrics:
      - id: "mo_2025-001-01"
        name: "Monthly customer churn"
        value: 3.2
        unit: "percent"
        period: { start: "2024-10-01", end: "2025-03-31" }
        target: 3.5
        sourceMetric: "ev_2025-001"
    links:
      - url: "https://metrics.acme.internal/churn/dashboard"
        label: "Internal dashboard (requires auth)"
    relatedRefs:
      - { id: "exp_201", type: "experience" }
      - { id: "claim_003", type: "careerClaim" }
    history:
      - { at: "2025-04-15T10:00:00Z", event: "created", detail: "by importer:resume-v2" }

  - id: "ev_2025-002"            # SUPPORTS exp_201 + skl_310 (cross-kind support)
    kind: github_repository
    title: "control-plane reliability playbook"
    summary: "Public repository of runbooks and SLO definitions used in production."
    provenance:
      source: { kind: url, id: "https://github.com/marachen/runbooks" }
      capturedAt: "2025-05-01T09:00:00Z"
      capturedBy: "agent:profile-enricher"
    verificationStatus: observed
    reviewState: approved
    links:
      - url: "https://github.com/marachen/runbooks"
        label: "Repository"
    relatedRefs:
      - { id: "exp_201", type: "experience" }
      - { id: "skl_310", type: "skill" }

  - id: "ev_2025-003"            # SUPPORTS professionalSummary
    kind: document
    title: "2025 annual performance review"
    summary: "Manager summary of impact and leadership."
    provenance:
      source: { kind: document, id: "doc_review_2025", label: "Annual review PDF" }
      capturedAt: "2025-02-10T00:00:00Z"
      capturedBy: "user:marachen"
    verificationStatus: user_confirmed
    reviewState: approved
    relatedRefs:
      - { id: "prof_marachen", type: "professionalSummary" }

  - id: "ev_2025-004"            # SUPPORTS exp_200
    kind: project
    title: "Payment reconciliation rewrite"
    summary: "Replaced batch reconciliation with streaming, cutting settlement lag to minutes."
    provenance:
      source: { kind: document, id: "doc_resume_2025-04", label: "Resume submitted 2025-04" }
      capturedAt: "2025-04-15T10:00:00Z"
      capturedBy: "importer:resume-v2"
    verificationStatus: imported
    reviewState: draft
    relatedRefs:
      - { id: "exp_200", type: "experience" }

  - id: "ev_2025-005"            # SUPPORTS cer_500 (verified path)
    kind: certification
    title: "CKA credential"
    summary: "Credential confirmed in the CNCF certification registry."
    provenance:
      source: { kind: system, id: "registry:cncf", label: "CNCF credential registry" }
      capturedAt: "2024-03-18T12:00:00Z"
      capturedBy: "verifier:credential-check"
    verificationStatus: verified
    reviewState: approved
    relatedRefs:
      - { id: "cer_500", type: "certification" }

  - id: "ev_2025-006"            # ORPHAN — supports nothing yet (unused evidence)
    kind: presentation
    title: "KubeCon 2024 talk: SLO-driven control planes"
    summary: "Conference talk slides and recording."
    provenance:
      source: { kind: url, id: "https://kubecon.example/2024/marachen" }
      capturedAt: "2025-05-01T09:05:00Z"
      capturedBy: "agent:profile-enricher"
    verificationStatus: observed
    reviewState: pending_review
    links:
      - url: "https://kubecon.example/2024/marachen"
        label: "Talk page"
    relatedRefs: []               # intentionally empty
```

## Reading the Example

### Many-to-many in action

- `ev_2025-001` (metric) supports **two** elements: `exp_201` and `claim_003`.
- `exp_201` is supported by **two** evidence items: `ev_2025-001` and
  `ev_2025-002`.

This is the core relationship of the model: one fact can back many claims, and
one claim can be backed by many facts.

### Confidence states on display

| Evidence | Status | Why |
|---|---|---|
| `ev_2025-005` | `verified` | confirmed against the CNCF registry |
| `ev_2025-002` / `ev_2025-006` | `observed` | captured directly from live URLs |
| `ev_2025-001` / `ev_2025-004` | `imported` | extracted from the resume |
| `ev_2025-003` | `user_confirmed` | the professional submitted and confirmed it |

No confidence **score** is computed anywhere — only the inputs are stored.

### Traceability path (worked example)

```
Artifact text: "Reduced customer churn by ~30%."
  ─ sourceRef ─▶ careerClaims/claim_003
  ─ evidenceRefs ─▶ evidence/ev_2025-001 (verificationStatus: imported)
  ─ provenance ─▶ document doc_resume_2025-04, captured 2025-04-15
```

A reader of the artifact sees only the statement. The knowledge layer can
resolve the full chain deterministically.

### Reasoning signals present

| Condition | Example in this profile |
|---|---|
| `strong_claim_without_evidence` | `exp_200` narrative claims impact but only has `ev_2025-004` (a project, no metrics) |
| `evidence_exists_but_unused` | `ev_2025-006` (KubeCon talk) supports nothing in any generated artifact |
| `experience_unsupported` | none — every experience has ≥1 evidence ref, but `exp_200` is thin (1 project, no measured outcomes) |
| `duplicate_evidence` | none — identity is unique per fact |
| `missing_measurable_outcomes` | `exp_200` implies "cut settlement lag to minutes" without a metric record |
