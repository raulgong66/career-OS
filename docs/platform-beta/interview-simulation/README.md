# Interview Simulation

## Purpose

Interview Simulation is a Platform Beta module that enables rehearsal, evaluation, and review of interview sessions using the Canonical Professional Profile as the authoritative knowledge source.

## Short description

Interview Simulation is a runtime activity that consumes professional knowledge, tracks interview session state, evaluates answers deterministically, and generates advisory reports. It is designed as a Core consumer, not as a parallel knowledge platform.

## Design Documents

- [01 Domain Model](01-domain-model.md)
- [02 Session Lifecycle](02-session-lifecycle.md)
- [03 Core Integration](03-core-integration.md)
- [04 Architecture](04-architecture.md)
- [05 API Proposal](05-api-proposal.md)
- [06 Implementation Guidelines](06-implementation-guidelines.md)
- [07 Session Engine Design](07-session-engine-design.md)
- [ADR-007: Interview Simulation & Session Lifecycle](../ADR-007-Interview-Simulation-and-Session-Lifecycle.md)

## Implementation Status

- ✓ Architecture (Frozen)
- □ Domain Models
- □ Session Engine
- □ Answer Evaluation
- □ REST API
- □ Frontend

## Future Scope

Interview Simulation fits inside Platform Beta as a Professional Activity layer that consumes the canonical profile and Core reasoning services. It complements Interview Intelligence and other future activities such as Career Planning, Learning Sessions, and Skill Assessment.
