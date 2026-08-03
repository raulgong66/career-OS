# Professional Knowledge Graph

A lightweight, immutable, in-memory knowledge graph layer connecting all
canonical CareerOS entities.

## Purpose

The graph provides a navigable, queryable view of the professional profile.
It is the foundation for:

- **AI Tailoring** — traverse skill→experience→organization to identify
  relevant evidence for a target role.
- **Recommendation Engine** — find adjacent skills, similar experiences, or
  complementary education.
- **Gap Analysis** — compare required vs. present skills/experience nodes.
- **Career Analytics** — aggregate statistics across the graph (tenure per
  org, skill distribution, etc.).
- **Agentic Workflows** — enable autonomous agents to walk relationships
  without re-parsing the profile dict.

## Graph Model

```
Person
 ├── HAS_EXPERIENCE ──► Experience ──► AT_ORGANIZATION ──► Organization
 ├── HAS_SKILL      ──► Skill     ──► USED_IN_EXPERIENCE ──► Experience
 └── HAS_EDUCATION  ──► Education ──► AT_ORGANIZATION ──► Organization

Experience ──► USES_SKILL ──► Skill
```

## Node Types

| Type | Label source | Key properties |
|---|---|---|
| `person` | First name in `names` array | `email`, `phone`, `location` |
| `experience` | Job title | `title`, `startDate`, `endDate`, `isCurrent`, `engagementType`, `scope`, `location` |
| `skill` | Skill name | `name`, `category`, `proficiency` |
| `education` | Degree/program name | `program`, `fieldOfStudy`, `startDate`, `endDate`, `isCurrent` |
| `organization` | Organization name | `name` |

## Edge Types

| Type | Source → Target | Cardinality |
|---|---|---|
| `HAS_EXPERIENCE` | Person → Experience | 1:N |
| `HAS_SKILL` | Person → Skill | 1:N |
| `HAS_EDUCATION` | Person → Education | 1:N |
| `USES_SKILL` | Experience → Skill | N:M (from skill evidence) |
| `USED_IN_EXPERIENCE` | Skill → Experience | N:M (inverse of USES_SKILL) |
| `AT_ORGANIZATION` | Experience → Organization | N:1 |
| `AT_ORGANIZATION` | Education → Organization | N:1 |

## Construction

`KnowledgeGraphBuilder.build(profile: dict) → KnowledgeGraph`

The builder is entirely deterministic. No LLM calls, no external APIs.
It reads existing reference fields in the canonical profile dict:

- `person.id` → person node
- `experiences[].organizationRefs` → AT_ORGANIZATION edges
- `skills[].extensions.experienceEvidence` → USES_SKILL / USED_IN_EXPERIENCE
- `education[].institutionRef` → AT_ORGANIZATION edges
- `organizations[]` → organization nodes

## Query API

```python
graph.skills()                                         # → list[GraphNode]
graph.experiences()                                    # → list[GraphNode]
graph.education()                                      # → list[GraphNode]
graph.organizations()                                  # → list[GraphNode]
graph.skill(name)                                      # → GraphNode | None
graph.skills_used_by(experience_id)                    # → list[GraphNode]
graph.experiences_using(skill_name)                    # → list[GraphNode]
graph.organizations_for_skill(skill_name)              # → list[GraphNode]
```

All name-based lookups are case-insensitive.

## Immutability

`KnowledgeGraph` exposes properties as defensive copies. Nodes and edges
are `@dataclass(frozen=True)`. Once built, the graph is read-only.

## Future Extensions

### New node types
Add a `GraphNode(..., type="certification")` during construction; the
`KnowledgeGraph` model has no hardcoded type restrictions — `skills()`
etc. are convenience filters.

### New relationship types
Add a `GraphEdge(...)` with the desired type string. The index will
automatically include it.

### Cross-entity enrichment
The `prepare()` method on builders is reserved for cross-builder data flow.
The graph builder can be extended to read `context` from `BuilderContext`
for additional relationships (e.g. `achievementRefs`, `evidenceRefs`).

## Package Structure

```
knowledge/
├── __init__.py          # Public API exports
├── models.py            # GraphNode, GraphEdge, KnowledgeGraph
├── builder.py           # KnowledgeGraphBuilder
└── README.md            # This file
```
