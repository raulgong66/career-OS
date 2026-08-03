from __future__ import annotations

from collections import deque

from .rule import Rule


class RegistryError(Exception):
    ...


class DuplicateRuleError(RegistryError):
    ...


class MissingDependencyError(RegistryError):
    ...


class CircularDependencyError(RegistryError):
    ...


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.id in self._rules:
            raise DuplicateRuleError(f"Rule '{rule.id}' is already registered")
        self._rules[rule.id] = rule

    def unregister(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def list(self) -> list[Rule]:
        return list(self._rules.values())

    def validate_dependencies(self) -> None:
        for rule in self._rules.values():
            for dep_id in rule.dependencies:
                if dep_id not in self._rules:
                    raise MissingDependencyError(
                        f"Rule '{rule.id}' depends on '{dep_id}' which is not registered"
                    )

    def execution_order(self) -> list[Rule]:
        self.validate_dependencies()
        return self._topological_sort()

    def _topological_sort(self) -> list[Rule]:
        in_degree: dict[str, int] = {rid: 0 for rid in self._rules}
        adjacency: dict[str, list[str]] = {rid: [] for rid in self._rules}

        for rule_id, rule in self._rules.items():
            for dep_id in rule.dependencies:
                if dep_id in adjacency:
                    adjacency[dep_id].append(rule_id)
                    in_degree[rule_id] += 1

        queue: deque[str] = deque(
            rid for rid, deg in in_degree.items() if deg == 0
        )
        sorted_ids: list[str] = []

        while queue:
            rid = queue.popleft()
            sorted_ids.append(rid)
            for neighbor in adjacency[rid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(self._rules):
            raise CircularDependencyError("Circular dependency detected among registered rules")

        return [self._rules[rid] for rid in sorted_ids]
