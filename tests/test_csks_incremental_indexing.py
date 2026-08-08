"""Tests for CSKS incremental indexing (M1.27).

The incremental indexer re-extracts only changed source files and reuses the
persisted per-source extraction artifacts for unchanged files. The resulting
graph must be identical to a full rebuild of the same repository state.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from careeros.csks import extractor
from careeros.csks.cli import CSKS_APP
from careeros.csks.indexer import CSKSIndexer


def _graph_signature(graph) -> tuple:
    nodes = tuple(sorted(
        (node.id, node.type, node.label, tuple(sorted((k, repr(v)) for k, v in node.properties.items())))
        for node in graph.nodes.values()
    ))
    edges = tuple(sorted(
        (edge.source_id, edge.target_id, edge.type, tuple(sorted((k, repr(v)) for k, v in edge.properties.items())))
        for edge in graph.edges
    ))
    return (nodes, edges)


def _full_rebuild(repo: Path) -> "object":
    return CSKSIndexer(repo).build_full_index()


def _change(repo: Path, rel: str) -> None:
    path = repo / rel
    path.write_text(path.read_text(encoding="utf-8") + "\n\nclass IncrementalMarker:\n    pass\n", encoding="utf-8")


def test_incremental_without_prior_index_builds_full(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    graph = indexer.incremental_update([])
    assert graph.node_count > 0
    assert _graph_signature(graph) == _graph_signature(_full_rebuild(csks_sample_repo))


def test_incremental_update_is_deterministic_and_idempotent(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()
    first = _graph_signature(indexer.incremental_update([]))
    second = _graph_signature(indexer.incremental_update([]))
    assert first == second


def test_incremental_update_only_reindexes_changed_file(csks_sample_repo: Path, monkeypatch) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()

    called: list[str] = []
    orig_entities = extractor.PythonASTExtractor.extract_entities
    orig_relationships = extractor.PythonASTExtractor.extract_relationships

    def spy_entities(self, source_path: str):
        called.append(str(source_path))
        return orig_entities(self, source_path)

    def spy_relationships(self, source_path: str):
        called.append(str(source_path))
        return orig_relationships(self, source_path)

    monkeypatch.setattr(extractor.PythonASTExtractor, "extract_entities", spy_entities)
    monkeypatch.setattr(extractor.PythonASTExtractor, "extract_relationships", spy_relationships)

    _change(csks_sample_repo, "careeros/profile_loader.py")
    graph = indexer.incremental_update([])

    assert called, "the changed file should have been re-extracted"
    assert all(path == "careeros/profile_loader.py" for path in called)
    assert indexer.get_entity("component.careeros.profile_loader.IncrementalMarker") is not None
    assert _graph_signature(graph) == _graph_signature(_full_rebuild(csks_sample_repo))


def test_incremental_update_explicit_changed_files(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()
    _change(csks_sample_repo, "careeros/profile_loader.py")
    graph = indexer.incremental_update(["careeros/profile_loader.py"])
    assert indexer.get_entity("component.careeros.profile_loader.IncrementalMarker") is not None
    assert _graph_signature(graph) == _graph_signature(_full_rebuild(csks_sample_repo))


def test_incremental_update_adds_file(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    before = indexer.build_full_index().node_count

    (csks_sample_repo / "careeros" / "new_module.py").write_text(
        "class NewWidget:\n    pass\n",
        encoding="utf-8",
    )

    graph = indexer.incremental_update([])
    assert graph.node_count > before
    assert indexer.get_entity("component.careeros.new_module.NewWidget") is not None
    assert _graph_signature(graph) == _graph_signature(_full_rebuild(csks_sample_repo))


def test_incremental_update_removes_file_and_orphaned_edges(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    full = indexer.build_full_index()
    before_nodes = full.node_count
    before_edges = full.edge_count

    target = "careeros/services/summarizer.py"
    assert indexer.get_entity("component.careeros.services.summarizer.summarize") is not None
    (csks_sample_repo / target).unlink()

    graph = indexer.incremental_update([])
    assert graph.node_count < before_nodes
    assert graph.edge_count < before_edges
    assert indexer.get_entity("component.careeros.services.summarizer.summarize") is None
    assert _graph_signature(graph) == _graph_signature(_full_rebuild(csks_sample_repo))


def test_incremental_update_metadata_accuracy(csks_sample_repo: Path) -> None:
    indexer = CSKSIndexer(csks_sample_repo)
    indexer.build_full_index()
    created_at = indexer._metadata.created_at
    updated_at = indexer._metadata.updated_at

    _change(csks_sample_repo, "careeros/widgets.py")
    graph = indexer.incremental_update([])

    metadata = indexer._metadata
    assert metadata.created_at == created_at
    assert metadata.updated_at >= updated_at
    assert metadata.entity_count == graph.node_count
    assert metadata.relationship_count == graph.edge_count

    rel = "careeros/widgets.py"
    assert rel in metadata.file_hashes
    expected_hash = indexer._compute_file_hashes()[rel]
    assert metadata.file_hashes[rel] == expected_hash

    persisted = indexer._metadata_path.read_text(encoding="utf-8")
    assert '"version": "1.0"' in persisted
    assert str(metadata.entity_count) in persisted


def test_incremental_equivalence_with_native_yaml_date(csks_sample_repo: Path) -> None:
    """A YAML native date scalar must not break full-vs-incremental equivalence.

    YAML/TOML parsers return ``datetime.date``/``datetime`` objects for
    unquoted dates. These are not JSON-native and must be normalized to
    strings before being persisted, otherwise the incremental graph diverges
    from a full rebuild of the same repository state.
    """
    (csks_sample_repo / "config.yaml").write_text(
        "launch_date: 2020-01-01\n"
        "name: sample\n",
        encoding="utf-8",
    )

    indexer = CSKSIndexer(csks_sample_repo)
    full = indexer.build_full_index()
    incremental = indexer.incremental_update([])

    assert _graph_signature(full) == _graph_signature(incremental)

    entity = indexer.get_entity("configuration.config.launch_date")
    assert entity is not None
    assert entity["properties"]["value"] == "2020-01-01"
    assert entity["properties"]["value_type"] == "date"


def test_cli_index_incremental(csks_sample_repo: Path) -> None:
    runner = CliRunner()
    first = runner.invoke(CSKS_APP, ["index", "--repo-root", str(csks_sample_repo)])
    assert first.exit_code == 0, first.output
    assert "Index built" in first.output

    second = runner.invoke(CSKS_APP, ["index", "--incremental", "--repo-root", str(csks_sample_repo)])
    assert second.exit_code == 0, second.output
    assert "Index built" in second.output
