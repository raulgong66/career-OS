from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


class KnowledgeGraph:
    """Immutable directed graph built from a canonical CareerOS profile."""

    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self._nodes: dict[str, GraphNode] = {}
        for n in nodes:
            if n.id in self._nodes:
                raise ValueError(f"Duplicate node ID: {n.id}")
            self._nodes[n.id] = n
        self._edges: list[GraphEdge] = list(edges)
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        for e in self._edges:
            self._outgoing[e.source_id].append(e)
            self._incoming[e.target_id].append(e)

    @property
    def nodes(self) -> dict[str, GraphNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[GraphEdge]:
        return list(self._edges)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def skill(self, skill_name: str) -> GraphNode | None:
        """Find a single skill node by its display name (case-insensitive)."""
        lower = skill_name.strip().lower()
        for n in self._nodes.values():
            if n.type == "skill" and n.label.lower() == lower:
                return n
        return None

    def skills(self) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.type == "skill"]

    def experiences(self) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.type == "experience"]

    def education(self) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.type == "education"]

    def organizations(self) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.type == "organization"]

    def skills_used_by(self, experience_id: str) -> list[GraphNode]:
        """Return all skill nodes used by the given experience."""
        result: list[GraphNode] = []
        for edge in self._outgoing.get(experience_id, []):
            if edge.type == "USES_SKILL":
                node = self._nodes.get(edge.target_id)
                if node is not None:
                    result.append(node)
        return result

    def experiences_using(self, skill_name: str) -> list[GraphNode]:
        """Return all experience nodes where the given skill was used."""
        skill = self.skill(skill_name)
        if skill is None:
            return []
        result: list[GraphNode] = []
        for edge in self._outgoing.get(skill.id, []):
            if edge.type == "USED_IN_EXPERIENCE":
                node = self._nodes.get(edge.target_id)
                if node is not None:
                    result.append(node)
        return result

    def organizations_for_skill(self, skill_name: str) -> list[GraphNode]:
        """Return all organizations associated with the given skill."""
        skill = self.skill(skill_name)
        if skill is None:
            return []
        seen: set[str] = set()
        result: list[GraphNode] = []
        for used_in_edge in self._outgoing.get(skill.id, []):
            if used_in_edge.type == "USED_IN_EXPERIENCE":
                exp_id = used_in_edge.target_id
                for org_edge in self._outgoing.get(exp_id, []):
                    if org_edge.type == "AT_ORGANIZATION":
                        org_id = org_edge.target_id
                        if org_id not in seen:
                            seen.add(org_id)
                            node = self._nodes.get(org_id)
                            if node is not None:
                                result.append(node)
        return result
