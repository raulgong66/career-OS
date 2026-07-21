"""Deterministic evidence selection for export contracts."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .export_contract import ExportContract, ExportSource


class EvidenceSelector:
    """Filter export sources before generator rendering."""

    def select(self, contract: ExportContract) -> ExportContract:
        """Return a copy of the contract with relevant sources preserved in order.

        The selector is intentionally deterministic. It does not rank, score, or call
        providers. Sources without target-context constraints are retained. Sources
        with target-context constraints are retained only when they match the
        artifact's target contexts.
        """
        target_context_ids = {
            str(context["id"])
            for context in contract.target_contexts
            if context.get("id")
        }
        selected_sources = [
            source
            for source in contract.sources
            if self._is_relevant(source, target_context_ids)
        ]
        return replace(contract, sources=selected_sources)

    def _is_relevant(self, source: ExportSource, target_context_ids: set[str]) -> bool:
        """Return whether a source is relevant for the target contexts."""
        source_context_ids = self._target_context_ids(source.ref) | self._target_context_ids(source.data)
        if not source_context_ids:
            return True
        if not target_context_ids:
            return False
        return bool(source_context_ids & target_context_ids)

    @staticmethod
    def _target_context_ids(payload: dict[str, Any]) -> set[str]:
        """Extract target-context ids from a schema-compatible payload."""
        return {
            str(ref["id"])
            for ref in payload.get("targetContextRefs", [])
            if isinstance(ref, dict) and ref.get("id")
        }
