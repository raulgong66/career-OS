from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class BuilderContext:
    organization_id_map: dict[str, str] = field(default_factory=dict)
    organization_names: dict[str, str] = field(default_factory=dict)
    experience_id_map: dict[str, str] = field(default_factory=dict)
    skill_id_map: dict[str, str] = field(default_factory=dict)


class BaseBuilder(ABC):
    entity_type: ClassVar[type]
    profile_key: ClassVar[str]
    extraction_field: ClassVar[str]
    singular: ClassVar[bool] = False

    @abstractmethod
    def normalize(self, items: list) -> list:
        ...

    def prepare(
        self,
        items: list,
        all_data: dict[type, list],
    ) -> list:
        return items

    @abstractmethod
    def build_many(
        self,
        items: list,
        context: BuilderContext,
    ) -> list[dict[str, Any]]:
        ...


class BuilderRegistry:
    def __init__(self) -> None:
        self._builders: dict[type, BaseBuilder] = {}
        self._order: list[type] = []

    def register(self, entity_type: type, builder: BaseBuilder) -> None:
        if not isinstance(builder, BaseBuilder):
            raise TypeError(
                f"Expected BaseBuilder instance, got {type(builder).__name__}"
            )
        if entity_type in self._builders:
            raise ValueError(
                f"Builder already registered for {entity_type.__name__}"
            )
        self._builders[entity_type] = builder
        self._order.append(entity_type)

    def get(self, entity_type: type) -> BaseBuilder | None:
        return self._builders.get(entity_type)

    def all(self) -> list[tuple[type, BaseBuilder]]:
        return [(t, self._builders[t]) for t in self._order]
