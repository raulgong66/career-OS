# Interview Simulation Architecture

This document describes the architecture of the Interview Simulation module and its relationship to Core, the API layer, and the frontend.

## Module boundaries

Interview Simulation is a platform module that depends on Core and exposes session capabilities to application layers. It does not depend on the frontend or API implementation details.

## Conceptual layers

The conceptual architecture for CareerOS is:

Professional Knowledge
↓
Professional Activities
↓
Documents

- **Professional Knowledge** is the Canonical Professional Profile and Core knowledge services.
- **Professional Activities** are runtime capabilities that consume professional knowledge without owning it.
- **Documents** are generated artifacts, summaries, and reports derived from activity state and knowledge.

Interview Simulation is a Professional Activity. It consumes professional knowledge through the Core services and produces documents such as session reports and summaries, but it never becomes the source of professional knowledge.

Examples of Professional Activities:

- Interview Simulation
- AI Tailoring
- Recruiter Assistant
- Learning Sessions
- Career Planning
- Skill Assessment

Activities may generate reports or artifacts, but they do not own the underlying knowledge.

## Dependency flow

Core
↓
Interview Simulation
↓
Future API
↓
Frontend

- Core provides canonical profile management, deterministic reasoning, evidence and claim models, export contract, generator registry, and provider abstractions.
- Interview Simulation consumes Core and implements session state, evaluation, feedback, and report generation.
- Future API exposes Interview Simulation capabilities to applications without introducing Core dependencies into the frontend.
- Frontend consumes the API to render session workflows, reports, and review interfaces.

## Ownership

- Core owns the canonical profile, knowledge graph, reasoning engine, evidence model, claim model, export contract, and generator registry.
- Interview Simulation owns session runtime state, question instance management, answer evaluation, feedback assembly, and session persistence strategy.
- Future API owns transport interfaces, session routing, and application-level orchestration.
- Frontend owns user experience and rendering of session state and reports.

## No dependency inversion

The architecture is intentionally layered. Core is the foundation. Interview Simulation depends on Core. Future API depends on Interview Simulation. Frontend depends on the API.

There is no inversion of this dependency direction.

## Architecture components

- `InterviewSession Engine`
  - Manages session lifecycle, question sequencing, answer collection, and metrics.
- `Evaluation Engine`
  - Applies deterministic rules and scoring to answers.
- `Feedback Layer`
  - Produces advisory guidance and review notes.
- `Report Generator`
  - Uses the Core export pipeline to create session reports and summaries.
- `Session Persistence`
  - Stores session state externally from the canonical profile.

## Relationship to existing Interview Intelligence

Interview Simulation is a new Core consumer alongside Interview Intelligence. It reuses `InterviewPlan` and the evidence/claim contracts defined by ADR-002 and ADR-003. It does not duplicate the intelligence layer; it consumes the same profile-driven reasoning foundation.

## Future API

The API layer will expose session creation, answer submission, session control, and report retrieval. The API is a thin application boundary. It maps API operations to the Interview Simulation engine without embedding evaluation policy or profile mutation logic.

## Frontend

The frontend renders session state, question prompts, answer forms, and reports. It remains a consumer of the API only.

## Diagram summary

The high-level architecture is:

- Core: platform foundation and knowledge services
- Interview Simulation: session logic, evaluation, reports
- Future API: transport and session endpoints
- Frontend: interactive user workflows
