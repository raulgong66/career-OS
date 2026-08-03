# Interview Intelligence — 05. API Proposal

Future REST endpoints. **Examples only — no implementation in M1.12.**

Conventions consistent with the existing API: paths under the profile resource where a profile is involved, module-scoped resource prefixes for interview objects, and the existing error surface (`NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`, `UNSUPPORTED_*`).

## A. Candidate Preparation

```
# Generate questions for a candidate (deterministic targeting + optional LLM phrasing)
POST /interviews/questions/generate
  body:  { profileId, types: ["technical","star",...], competencies: ["kubernetes","aws"], role?: string, count?: number }
  resp:  { questions: [InterviewQuestion] }

GET /interviews/questions/{questionId}
  resp: { question, competencyRefs, contextRefs, expected }

# Build a preparation guide and persist it as an artifact (artifact lifecycle)
POST /interviews/preparation-guides
  body:  { profileId, targetRole?: string, competencies?: [], includeAnswers?: boolean }
  resp:  { guideId, artifactId, artifactStatus }

GET /interviews/preparation-guides/{guideId}
  resp:  { guide, questions, suggestedAnswers, evidenceToCite, weakAreas }
```

## B. Interview Simulation

```
# Start / drive a session
POST /interviews/sessions
  body:  { profileId, planId?: string, mode: "simulation", targetRole?: string }
  resp:  { sessionId, status, currentQuestion }

POST /interviews/sessions/{sessionId}/answers
  body:  { questionId, answer }
  resp:  { feedback, evaluation, citations, followUp }

POST /interviews/sessions/{sessionId}/followup
  body:  { questionId }
  resp:  { followUpQuestion }

GET /interviews/sessions/{sessionId}
  resp:  { session, questions, answers }

# Completed session → immutable report (persisted as artifact)
POST /interviews/sessions/{sessionId}/report
  resp:  { reportId, artifactId, artifactStatus }

GET /interviews/reports/{reportId}
  resp:  { report }
```

## C. Recruiter Assistant

```
# Ask a recruiter question; answer is grounded in the canonical profile with citations
POST /interviews/recruiter/query
  body:  { profileId, question }
  resp:  { answer, citations, profileGaps: [] }

# Targeted lookups (deterministic, no NLU required)
GET /profiles/{profileId}/evidence?skill=kubernetes
  resp: { evidence: [ {id, title, verificationStatus, ...} ] }

GET /profiles/{profileId}/achievements/measurable
  resp: { achievements: [ {id, statement, metrics, contextRefs} ] }

GET /profiles/{profileId}/leadership
  resp: { findings: [ {sourceRef, signals, evidenceRefs} ] }
```

## Module-Local Persistence vs Canonical Profile

- Sessions, questions, answers, feedback, and reports are **module-local** state.
- Prep guides and reports that should be recruiter/candidate-visible documents are persisted as **artifacts** through the existing lifecycle (validated, with `status` current/stale and explicit regeneration).
- The module never exposes an endpoint that writes the canonical profile; profile changes flow through the existing review workflow.

## Design Constraints Honored

1. No new transport concepts; reuse the FastAPI error surface and DTO pattern.
2. All recruiter responses carry citations to canonical elements/evidence.
3. Evaluation responses expose qualitative levels only — no numeric scores.
4. LLM-assisted phrasing endpoints are explicit (e.g. `generate`, `followup`) and always deterministic-first.
