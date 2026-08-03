from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ReasoningResult, RuleContext


class Rule(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def dependencies(self) -> list[str]:
        return []

    @abstractmethod
    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        ...
