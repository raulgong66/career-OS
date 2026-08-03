# CSKS API Reference

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer

The CSKS REST API is mounted as the `/csks` router in the main FastAPI app.

| Method | Path | Purpose |
|---|---|---|
| GET | `/csks/query?q={question}` | Execute a query, return a structured answer |
| GET | `/csks/entity/{entity_id}` | Get a single entity with its relationships |
| GET | `/csks/search` | Search entities (faceted and/or grouped) |
| GET | `/csks/status` | Index status |

## `GET /csks/query`

**Query parameter**: `q` — the natural-language or structured question.

**Response**:

```json
{
  "answer": "Component: ProfileLoader (component.careeros.profile_loader.ProfileLoader)\n  Type: class\n...",
  "citations": [
    {
      "file": "careeros/profile_loader.py",
      "line_start": 16,
      "line_end": 62,
      "text": "ProfileLoader - component",
      "entity_id": "component.careeros.profile_loader.ProfileLoader"
    }
  ],
  "confidence": 1.0,
  "entities_found": 1,
  "query_time_ms": 12,
  "query_type": "entity_lookup"
}
```

**`query_type` values**: `entity_lookup`, `type_filter`,
`dependency_traversal`, `reverse_dependency` *(M1.23)*, `impact_analysis`,
`data_flow_path`, `search` *(M1.23)*, `capability_check`, `status_check`,
`unknown`.

Examples:

```text
GET /csks/query?q=What%20is%20ProfileLoader%3F
GET /csks/query?q=List%20API%20endpoints.
GET /csks/query?q=What%20does%20ArtifactGenerator%20depend%20on%3F
GET /csks/query?q=Search%20profile.
```

## `GET /csks/entity/{entity_id}`

Returns a single entity with its outgoing/incoming relationships.

**Response**:

```json
{
  "id": "component.careeros.profile_loader.ProfileLoader",
  "type": "component",
  "label": "ProfileLoader",
  "properties": { "...": "..." },
  "outgoing_relationships": [ { "type": "...", "target": "...", "properties": {} } ],
  "incoming_relationships": [ { "type": "...", "source": "...", "properties": {} } ]
}
```

Returns `404` when the entity is not found.

## `GET /csks/search`

Supports two modes:

### Grouped search (M1.23) — with `q`

```text
GET /csks/search?q=profile&limit=100
```

**Response**:

```json
{
  "groups": {
    "Domains": [
      {
        "id": "domain.profile_management",
        "type": "domain",
        "label": "Profile Management",
        "file": "docs/architecture/02-domain-map.md",
        "line_start": 15,
        "line_end": 15,
        "location": "docs/architecture/02-domain-map.md:15"
      }
    ],
    "Components": [ "...", "..." ]
  },
  "total": 42
}
```

### Faceted search (M1.22 behavior) — without `q`

```text
GET /csks/search?type=domain&domain=&limit=50
```

**Response**:

```json
{
  "results": [ { "id": "...", "type": "...", "label": "...", "properties": {} } ],
  "count": 8
}
```

| Parameter | Description |
|---|---|
| `q` | Search term; when present, returns grouped results. |
| `type` | Filter by entity type (faceted mode only). |
| `domain` | Filter by domain property (faceted mode only). |
| `limit` | Maximum results, 1..500 (default 50). |

## `GET /csks/status`

**Response**:

```json
{
  "status": "ready",
  "entity_count": 4323,
  "relationship_count": 1320,
  "git_commit": "459d939...",
  "indexed_files": 127,
  "last_build_ms": 8000,
  "created_at": 0.0,
  "updated_at": 0.0
}
```

## Compatibility

- The response shapes of `/csks/query`, `/csks/entity`, `/csks/status`, and the
  faceted mode of `/csks/search` are unchanged from M1.22.
- M1.23 adds only: two new `query_type` values (`reverse_dependency`, `search`)
  and the optional `q` parameter on `/csks/search`.
