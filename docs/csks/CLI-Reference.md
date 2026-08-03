# CSKS CLI Reference

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer

The CSKS CLI is a Typer sub-app of the main `careeros` CLI.

```bash
careeros csks --help
```

## Commands

### `careeros csks index`

Build the full CSKS index from all sources.

```bash
careeros csks index [--repo-root PATH]
```

Prints the number of nodes and edges in the resulting knowledge graph.

| Option | Description |
|---|---|
| `--repo-root PATH` | Repository root. Defaults to the package root. |

### `careeros csks query`

Answer a natural-language or structured question against the knowledge graph.

```bash
careeros csks query "What is ProfileLoader?" [--repo-root PATH] [--json]
```

| Option | Description |
|---|---|
| `--repo-root PATH` | Repository root. Defaults to the package root. |
| `--json` | Emit the result as JSON instead of text. |

Example:

```bash
$ careeros csks query "What is ADR-008?"
ADR-008 (adr.008)
  Title: CareerOS Self-Knowledge System (CSKS) Foundation
  Status: Accepted
  Source: docs/adr/ADR-008-CSKS-Foundation.md:1
...
```

### `careeros csks search`

Search the knowledge graph.

```bash
careeros csks search <term>            # grouped results
careeros csks search --type domain     # faceted search (M1.22 behavior)
```

| Option | Description |
|---|---|
| `term` (positional) | Search term; produces grouped results across entity types. |
| `--type TYPE` | Filter by entity type (used when no term is given). |
| `--domain DOMAIN` | Filter by domain property. |
| `--limit N` | Maximum number of results (default 50). |
| `--repo-root PATH` | Repository root. Defaults to the package root. |

Example:

```bash
$ careeros csks search profile
Search results for "profile":
Domains:
  - Profile Management (domain.profile_management) — docs/architecture/02-domain-map.md:15
Components:
  ...
Total matches: N
```

Groups printed: Domains, Components, APIs, Schemas, Rules, Generators, Tests,
Milestones, ADRs, CLI commands, Configurations, Documents.

### `careeros csks entity`

Show a single entity and its relationships.

```bash
careeros csks entity <entity_id> [--repo-root PATH]
```

Exit code 1 when the entity does not exist.

### `careeros csks status`

Show the current CSKS index status (entity count, relationship count, git
commit, indexed files, build time).

```bash
careeros csks status [--repo-root PATH]
```

## Exit codes

- `0` on success.
- `1` when an `entity` lookup fails or a hard error occurs.
