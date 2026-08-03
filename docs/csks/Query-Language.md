# CSKS Query Language

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer

CSKS uses a **deterministic query grammar**: questions are classified by ordered,
first-match-wins rules. The same question always produces the same answer.

## 1. Intent categories

| Intent | `query_type` | Example |
|---|---|---|
| Component lookup | `entity_lookup` | `What is ProfileLoader?` |
| Domain lookup | `entity_lookup` | `What is Profile Management?` |
| Listing | `type_filter` | `List generators.` |
| Dependency analysis | `dependency_traversal` | `What depends on ProfileLoader?` |
| Reverse dependency | `reverse_dependency` | `What does ArtifactGenerator depend on?` |
| Impact analysis | `impact_analysis` | `What breaks if I change ProfileLoader?` |
| Data flow | `data_flow_path` | `How is a CV generated?` |
| Search | `search` | `Search profile.` |
| Capability check | `capability_check` | `Does CareerOS support PDF generation?` |
| Status check | `status_check` | `M1.22 status` |
| Not understood | `unknown` | `potato potato` |

## 2. Entity lookup

Triggers: `what is`, `what are`, `who is`, `define`, `describe`, `explain`,
`tell me about`, `show me`.

```text
What is ProfileLoader?
What is the TotalYearsExperienceRule?
What is ADR-008?
What is M1.22?
Describe ProfileLoader.
Explain ProfileLoader.
What is Profile Management?
```

Identifiers are normalized: `ADR-008`, `ADR 008`, `ADR008`, and `adr.008` all
resolve to `adr.008`. Milestones resolve by tag prefix: `M1.22` →
`milestone.m1.22-csks-foundation`. Canonical domain names (`Knowledge Layer`,
`Reasoning Engine`, `Interview Intelligence`, ...) resolve via the alias registry.

## 3. Listing

Triggers: `list`, `list all`, `show all`, `enumerate`, or a bare type noun.

```text
List domains.
List generators.
List API endpoints.
List reasoning rules.
List ADRs.
List milestones.
List schemas.
List tests.
cli commands
endpoints for profiles
```

## 4. Dependency analysis

Triggers: `what depends on`, `depends upon`, `what uses`, `who uses`, `what
imports`, `who consumes`, `consumers of`, `used by`.

```text
What depends on ProfileLoader?
What depends on Profile Management?
Who uses the ExportContract?
```

## 5. Reverse dependency

Triggers: `what does X depend on`, `what do X depend on`, `what are the
dependencies of X`, `dependencies of X`, `imports of X`.

```text
What does ArtifactGenerator depend on?
What are the dependencies of ProfileLoader?
```

## 6. Impact analysis

Triggers: `what breaks if`, `what happens if ... change`, `impact of changing`,
`affected by`.

```text
What breaks if I change ProfileLoader?
What is the impact of modifying the EvidenceSelector?
What would break if I refactor ProfileLoader?
```

## 7. Data flow

Triggers: `how does X work`, `how is X generated`, `walk me through X`, `data
flow for X`, `flow for X`, `pipeline for X`, `steps in X`, `explain how X`.

Known flows:

| Flow topic | Query example |
|---|---|
| artifact generation | `How does artifact generation work?` |
| cv | `How is a CV generated?` |
| interview preparation | `Walk me through interview preparation.` |
| acquisition | `Data flow for acquisition` |
| reasoning | `Flow for reasoning` |

```text
Data flow for artifact generation
How does artifact generation work?
How is a CV generated?
Walk me through interview preparation.
Explain how artifact generation works.
```

## 8. Search

Triggers: `search X`, `search for X`, `find X`. Returns grouped results.

```text
Search profile.
Search interview.
find artifact
```

The CLI command `careeros csks search <term>` produces identical grouped output.

## 9. Capability check

Triggers: `does ... support`, `can ... support`, `capability`, `supports ...
generation`.

```text
Does CareerOS support PDF generation?
Does CSKS support LLM integration?
Does CareerOS support X-ray vision?   -> "Unknown capability ..."
```

## 10. Status check

Triggers: `status`, `version`, `tag`, or a milestone number.

```text
M1.22 status
M1.21 status
status of the moon   -> "Unknown status ..."
```

## 11. Unknown queries

If no rule matches, CSKS answers:

```text
I could not classify your query.
Did you mean:
  - What is <topic>?
  - List <type>s.
  - What depends on <entity>?
  - What does <entity> depend on?
  - Search <term>.
```

## 12. Resolution precedence

When a question names an entity, resolution tries, in order:

1. Exact graph label match.
2. Exact graph id / id-suffix match.
3. Normalized identifier match (`adr.008`-style).
4. Alias-registry direct match (canonical domain names).
5. Alias-registry cluster rule (e.g. Interview Intelligence components).
6. Milestone/ADR tag-prefix match.
7. `Could not find entity matching: ...`

## 13. QueryType values

`entity_lookup`, `type_filter`, `dependency_traversal`, `reverse_dependency`,
`impact_analysis`, `data_flow_path`, `search`, `capability_check`, `status_check`,
`unknown`.
