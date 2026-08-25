"""Regression tests for the application_usage intent.

``How is X applied?`` queries must be classified as ``application_usage``
instead of falling through to other intents, and must reach the query
engine without crashing even when the graph lacks related content.

The tests build a small graph by hand so the classification decision is
fully controlled and independent of the sample-repo contents.
"""

from __future__ import annotations

from pathlib import Path

from careeros.csks.query import CSKSQueryEngine
from careeros.knowledge import GraphNode, KnowledgeGraph


def _node(
    entity_id: str,
    etype: str,
    label: str,
    source_path: str,
    line_start: int = 1,
    line_end: int = 1,
    **extra,
) -> GraphNode:
    props = {
        "source_path": source_path,
        "line_start": line_start,
        "line_end": line_end,
    }
    props.update(extra)
    return GraphNode(entity_id, etype, label, props)


def _flow_graph_nodes() -> list[GraphNode]:
    """Authoritative implementation nodes for a data flow."""
    return [
        _node(
            "component.careeros.profile_quality.engine.ProfileQualityEngine",
            "component",
            "ProfileQualityEngine",
            "careeros/profile_quality/engine.py",
            line_start=39,
            line_end=86,
        ),
        _node(
            "component.careeros.reasoning.findings.ProfileRecommendations",
            "component",
            "ProfileRecommendations",
            "careeros/reasoning/findings.py",
            line_start=84,
            line_end=115,
        ),
        _node(
            "component.careeros.reasoning.findings.ReasoningFindings",
            "component",
            "ReasoningFindings",
            "careeros/reasoning/findings.py",
            line_start=10,
            line_end=49,
        ),
    ]


# --- "How is AI applied?" ----------------------------------------------------


def test_how_is_ai_applied_unchanged(tmp_path: Path) -> None:
    graph = KnowledgeGraph(_flow_graph_nodes(), [])
    engine = CSKSQueryEngine(graph, repo_root=tmp_path)

    result = engine.query("How is AI applied?")

    # The query is now classified as application_usage (not data_flow_path)
    # The test graph lacks AI-related content, so we verify the intent classification
    assert result.query_type == "application_usage"
