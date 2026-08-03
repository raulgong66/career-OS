"""Grouped, deterministic term search over the CSKS knowledge graph (M1.23).

Provides the shared ``grouped_search`` used by both the ``careeros csks
search <term>`` CLI command and the ``search`` query intent. Matching is
plain substring/prefix/exact over node ids and labels — no embeddings, no
fuzzy matching.
"""

from __future__ import annotations

import re

GROUP_ORDER = (
    "Domains",
    "Components",
    "APIs",
    "Schemas",
    "Rules",
    "Generators",
    "Tests",
    "Milestones",
    "ADRs",
    "CLI commands",
    "Configurations",
    "Documents",
)

_TYPE_TO_GROUP = {
    "domain": "Domains",
    "component": "Components",
    "api_endpoint": "APIs",
    "schema": "Schemas",
    "rule": "Rules",
    "generator": "Generators",
    "test": "Tests",
    "milestone": "Milestones",
    "adr": "ADRs",
    "cli_command": "CLI commands",
    "configuration": "Configurations",
    "document": "Documents",
}

_SEARCHABLE_TYPES = frozenset(_TYPE_TO_GROUP)


def _tokens(term: str) -> list[str]:
    """Split a search term into lowercase tokens (minimum length 1)."""
    parts = re.split(r"[^a-z0-9]+", term.lower())
    return [p for p in parts if p]


def _rank(node, term_lower: str) -> int:
    """Deterministic relevance rank: 0 exact, 1 prefix, 2 substring."""
    label = node.label.lower()
    node_id = node.id.lower()
    if label == term_lower or node_id == term_lower:
        return 0
    if label.startswith(term_lower) or node_id.startswith(term_lower):
        return 1
    return 2


def grouped_search(graph, term: str, per_group: int = 10, limit: int = 100) -> dict:
    """Return grouped search results for ``term``.

    Returns ``{"groups": {name: [item, ...]}, "total": int}`` where each item
    is ``{"id", "type", "label", "location", "file", "line_start",
    "line_end"}``. Only non-empty groups are included, ordered by
    ``GROUP_ORDER``.
    """
    tokens = _tokens(term)
    if not tokens:
        return {"groups": {}, "total": 0}
    term_lower = term.lower()

    buckets: dict[str, list] = {}
    total = 0
    for node in graph.nodes.values():
        if node.type not in _SEARCHABLE_TYPES:
            continue
        haystack = f"{node.id} {node.label}".lower()
        if not all(tok in haystack for tok in tokens):
            continue
        group = _TYPE_TO_GROUP[node.type]
        item = {
            "id": node.id,
            "type": node.type,
            "label": node.label,
            "file": node.properties.get("source_path", ""),
            "line_start": node.properties.get("line_start", 0),
            "line_end": node.properties.get("line_end", 0),
            "location": f"{node.properties.get('source_path', '')}:{node.properties.get('line_start', 0)}",
        }
        buckets.setdefault(group, []).append(item)
        total += 1

    groups: dict[str, list] = {}
    for group_name in GROUP_ORDER:
        items = buckets.get(group_name)
        if not items:
            continue
        items.sort(key=lambda i: (_rank_for(i["id"], i["label"], term_lower), len(i["label"]), i["label"]))
        groups[group_name] = items[:per_group]

    # Respect the global limit across all groups.
    global_items = [(name, item) for name in groups for item in groups[name]]
    if len(global_items) > limit:
        truncated = {}
        remaining = limit
        for name in GROUP_ORDER:
            if name not in groups:
                continue
            take = min(remaining, len(groups[name]))
            if take > 0:
                truncated[name] = groups[name][:take]
                remaining -= take
        groups = truncated

    return {"groups": groups, "total": total}


def _rank_for(item_id: str, item_label: str, term_lower: str) -> int:
    """Rank a single search item by its id/label (exact > prefix > substring)."""
    label = item_label.lower()
    if label == term_lower or item_id.lower() == term_lower:
        return 0
    if label.startswith(term_lower) or item_id.lower().startswith(term_lower):
        return 1
    return 2
