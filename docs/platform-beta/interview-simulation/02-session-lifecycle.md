# Interview Simulation Session Lifecycle

This document defines the lifecycle of Interview Simulation sessions.

Interview sessions are runtime objects that represent the progress of a simulated interview. They are not part of the canonical profile, and they are persisted as external session state separate from profile content.

## Session states

- `Draft`
  - Session metadata is defined, the plan is selected, and the session is being configured.
- `Ready`
  - The session is prepared for execution and all required input has been collected.
- `In Progress`
  - The session is actively executing questions and collecting answers.
- `Paused`
  - The session has been temporarily stopped and can be resumed.
- `Completed`
  - All planned questions are answered or the session was intentionally ended.
- `Reviewed`
  - The session has been assessed by a human reviewer or architecture reviewer.
- `Archived`
  - The session is retained for historical reference and is no longer active.

## State transitions

Allowed transitions are:

- `Draft` → `Ready`
- `Ready` → `In Progress`
- `In Progress` → `Paused`
- `Paused` → `In Progress`
- `In Progress` → `Completed`
- `Ready` → `Completed` (for fast-path sessions)
- `Completed` → `Reviewed`
- `Reviewed` → `Archived`
- `Completed` → `Archived`

Terminal states:

- `Archived` is terminal.
- `Reviewed` is effectively terminal for active session processing, but it may be reopened for follow-up review if explicitly required.

## Partial completion and interruption recovery

Interview Simulation supports partial completion and interruption recovery.

- Partial completion occurs when a session is paused or intentionally ended before all questions are answered.
- Paused sessions preserve the current question index, answered questions, evaluation results, and metrics.
- Resume restores the session from persisted state and continues from the last recorded question.
- If the session is interrupted unexpectedly, the persisted runtime state is sufficient to recover the session without recomputing prior answers.

## Multiple sessions

A profile may have multiple sessions over time.

- Each `InterviewSession` is independent and identified by a unique session ID.
- Multiple sessions can coexist for the same profile to support repeated practice, different preparation angles, or review iterations.
- Session history is preserved without altering the canonical profile.

## Persistence model

Persistent session data includes:

- session metadata (`id`, `profile reference`, `plan reference`, creation timestamps)
- session status and state
- question instances and answer history
- answer evaluations and feedback
- session metrics and completion timestamps
- generated report and summary metadata

Transient runtime data includes:

- live AI prompt state
- temporary UI interaction context
- ephemeral completion drafts
- in-progress local rendering state

## Restart behavior

Restart choices are:

- `Completed` → new session creation
- `Reviewed` → new session creation for follow-up practice
- `Archived` → immutable historical record; no restart from archived session

Archived sessions remain as historical reference only. New work always begins in a new `InterviewSession`.

## Session lifecycle principles

- Session state is independent of the canonical profile.
- Runtime interruptions are recoverable through persisted session state.
- Review and archive are part of the lifecycle, not byproducts of execution.
- Multiple sessions are supported without introducing duplicate profile data.
