# Interview Simulation API Proposal

This document proposes the API responsibilities for Interview Simulation. It is a design proposal only.

## REST resources

### POST /interviews/sessions

Creates a new `InterviewSession`.

Responsibilities:
- select or validate the `InterviewPlan`
- associate the session with a profile reference
- persist session metadata and initial state
- return the session identifier and initial state

### POST /interviews/sessions/{id}/answers

Submits an answer for the current question.

Responsibilities:
- record the answer text and evidence references
- validate answer structure and evidence contract compliance
- persist the answer in session state
- return updated session status and evaluation markers

### POST /interviews/sessions/{id}/next

Advances the session to the next question or completes the session.

Responsibilities:
- apply session sequencing rules
- compute answer evaluation for the previous question
- update session metrics and next question state
- return the next question or completion status

### POST /interviews/sessions/{id}/pause

Pauses an in-progress session.

Responsibilities:
- persist the current session state
- mark the session as paused
- allow later resumption without data loss

### POST /interviews/sessions/{id}/resume

Resumes a paused session.

Responsibilities:
- restore the session from persisted state
- mark the session as in progress
- return the current question and evaluation context

### GET /interviews/sessions/{id}

Retrieves the current session state.

Responsibilities:
- return session metadata, question instances, answers, metrics, and status
- omit transient runtime details
- preserve canonical evidence references without duplicating profile content

### GET /interviews/sessions/{id}/report

Retrieves the session report.

Responsibilities:
- return the generated `InterviewReport` or `InterviewSummary`
- include evaluation findings, evidence alignment, and recommended next steps
- preserve the distinction between advisory feedback and canonical profile assertions

## API responsibilities only

The API layer is responsible for transport and orchestration. It does not implement deterministic evaluation policy, evidence contracts, or profile mutation rules. Those responsibilities remain in Core and the Interview Simulation engine.

## Session endpoint design principles

- Keep the API thin and behaviorless.
- Treat session state as external runtime state, not profile state.
- Preserve canonical evidence references in responses.
- Use clear resource semantics: sessions, answers, control actions, reports.
