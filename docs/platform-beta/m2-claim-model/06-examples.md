# M2 Examples — The Professional Claim Model

## Status

Illustrative examples across professions. Not a fixture, not an implementation.

Each example shows the pattern:

```
Evidence ─supports─▶ Claim ─used in─▶ Contexts
```

## 1. Platform Engineer (Kubernetes)

### Evidence (ADR-002)

| Evidence | Kind | Verification status |
|---|---|---|
| GitHub repository: `enterprise-kubernetes-platform` | `github_repository` | `observed` |
| Production deployment records (multi-tenant control plane) | `production_deployment` | `verified` |
| Customer testimonial ("cut their release cycle by half") | `customer_feedback` | `user_confirmed` |

### Claim

```yaml
id: claim_004
statement: "Designed and implemented an enterprise Kubernetes platform."
category: product_built
strength: strong
evidenceRefs: [ev_repo, ev_deploy, ev_testimonial]
targetContexts: [cv, linkedin, biography, interview_answers, technical_profile]
status: approved
```

### Used in

- **CV** — lead bullet under the current experience.
- **LinkedIn** — summary paragraph opener.
- **Biography** — headline sentence for speaking engagements.
- **Interview** — framing for the "tell me about your biggest build" answer.
- **Technical Profile** — proof section citing the repository and deployment
  records.

### Second claim from the same experience

```yaml
id: claim_003
statement: "Reduced production deployment time by 60% by automating release pipelines."
category: quantified_outcome
strength: exceptional
evidenceRefs: [ev_deploy]        # deployment log + metric evidence
targetContexts: [cv, interview_answers]
status: approved
```

One evidence item (`ev_deploy`) supports two claims — demonstrating
many-to-many support (R2.1).

## 2. Data Scientist

### Evidence

- Publication: "Forecasting demand with gradient-boosted ensembles" (`publication`, `verified`)
- Kaggle competition result / award (`award`, `observed`)
- Production model performance report (`metric`, `imported`)

### Claim

```yaml
id: claim_007
statement: "Built ML models that improved forecast accuracy by 20% against baseline."
category: quantified_outcome
strength: strong
evidenceRefs: [ev_paper, ev_kaggle, ev_metric]
targetContexts: [linkedin, portfolio, cv, interview_answers]
status: approved
```

### Used in

- **Portfolio** — project showcase with the paper and notebook links.
- **LinkedIn** — featured-post description.
- **Interview** — STAR-format anchor with the accuracy metric.

## 3. Sales & Account Growth

### Evidence

- KPI dashboard export: ARR growth (`kpi`, `verified` via CRM export)
- Customer feedback / renewal note (`customer_feedback`, `user_confirmed`)
- Award: "Top Regional Performance" (`award`, `observed`)

### Claim

```yaml
id: claim_010
statement: "Grew annual recurring revenue by 35% year over year as first AE on the account."
category: quantified_outcome
strength: exceptional
evidenceRefs: [ev_arr_kpi, ev_renewal, ev_award]
targetContexts: [executive_profile, cv, linkedin]
status: approved
```

### Used in

- **Executive Profile** — opening quantified headline.
- **CV** — top-of-experience achievement line.
- **LinkedIn** — headline/pinned post.

## 4. Healthcare Professional (Nurse Manager)

### Evidence

- Certification: BLS/ACLS records (`certification`, `verified`)
- Performance review note on the quality initiative (`document`, `user_confirmed`)
- Hospital quality metric report (`metric`, `imported`)

### Claim

```yaml
id: claim_012
statement: "Led a quality-improvement initiative that reduced average patient wait times by 15%."
category: leadership
strength: strong
evidenceRefs: [ev_cert, ev_review, ev_quality]
targetContexts: [cv, professional_summary, interview_answers]
status: reviewed
```

### Used in

- **Professional Summary** — highlighted accomplishment line.
- **Interview** — leadership example.
- **CV** — achievement bullet.

## 5. Same Evidence, Multiple Claims (many-to-many in action)

| Evidence | Supports | Claims |
|---|---|---|
| `ev_deploy` (production deployment) | claim_004, claim_003 | platform build; 60% deployment reduction |
| `ev_metric` (accuracy report) | claim_007 | forecast accuracy |

Two claims, one shared evidence item — and the ADR-002 reverse index
(`relatedRefs`) lists both claims on the evidence item. This is the canonical
shape the Reasoning Engine consumes.

## 6. Lifecycle Trace on the Kubernetes Claim

```
generated  (LLM proposes "Designed and implemented an enterprise Kubernetes platform.")
   │  reviewer requested
   ▼
reviewed   (reviewer cross-checks repo + deployment + testimonial)
   │  approved
   ▼
approved   (eligible for cv, linkedin, biography, interview_answers, technical_profile)
   │  testimonial withdrawn → reasoning engine flags
   ▼
deprecated (owner confirms; claim drops out of new documents but is retained)
   │
   ▼
archived   (administrator archives after retention; history preserved)
```

## Takeaways

1. Evidence is shared and reusable across claims (many-to-many).
2. The same claim appears in many contexts without duplication — the contexts
   reference the claim, they do not copy its text.
3. `strength`/`confidence` reflect the evidence set (measured outcomes,
   verification status) plus review state — qualitatively, never as a computed
   number.
4. A `reviewed` claim (healthcare example) is the boundary case the reasoning
   engine may or may not surface, depending on the override policy in
   `04-claim-lifecycle.md`.
