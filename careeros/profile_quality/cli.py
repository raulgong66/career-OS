"""CLI render helpers for profile quality commands (M1.24 Spec SS3.7, SS9.1).

Pure render helpers consumed by ``careeros_cli.main``. Output is either the
specified JSON shape (matching the REST API) or a rich table.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

from .dimensions import DIMENSION_LABELS
from .engine import run_profile_quality
from .unified import filter_and_sort_recommendations, to_unified_recommendations

_console = Console()


def profile_health_data(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the profile-health JSON payload (spec SS9.2)."""
    report = run_profile_quality(profile)
    return {
        "health_score": report.health_score,
        "dimensions": [
            {"name": dimension.name, "score": dimension.score, "weight": dimension.weight}
            for dimension in report.dimension_scores
        ],
        "findings": [finding.to_dict() for finding in report.findings],
        "citations": [citation.to_dict() for citation in report.citations],
    }


def print_profile_health(profile: dict[str, Any], *, output: str = "json") -> None:
    """Render ``careeros profile-health`` output."""
    data = profile_health_data(profile)
    if output == "table":
        table = Table(title="Resume Health")
        table.add_column("Dimension")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right")
        table.add_column("Findings", justify="right")
        for dimension in data["dimensions"]:
            table.add_row(
                DIMENSION_LABELS.get(dimension["name"], dimension["name"]),
                f"{dimension['score']:.2f}",
                f"{dimension['weight']:.2f}",
                "0",
            )
        _console.print(table)
        return
    _console.print_json(json.dumps(data))


def print_improvement_queue(
    profile: dict[str, Any],
    *,
    priority: str | None = None,
    resolution_type: str | None = None,
    output: str = "json",
) -> None:
    """Render ``careeros improvement-queue`` output."""
    report = run_profile_quality(profile)
    recommendations = filter_and_sort_recommendations(
        to_unified_recommendations(report),
        priority=priority,
        resolution_type=resolution_type,
    )
    if output == "table":
        table = Table(title="Improvement Queue")
        table.add_column("Rule ID")
        table.add_column("Element")
        table.add_column("Resolution")
        table.add_column("Priority")
        table.add_column("Title")
        for recommendation in recommendations:
            table.add_row(
                recommendation.rule_id,
                recommendation.element_id,
                recommendation.resolution_type,
                recommendation.priority,
                recommendation.title,
            )
        _console.print(table)
        return
    _console.print_json(json.dumps([r.to_dict() for r in recommendations]))


__all__ = [
    "print_improvement_queue",
    "print_profile_health",
    "profile_health_data",
]
