from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from careeros.knowledge import KnowledgeGraph

from .builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from .query import CSKSQueryEngine


@dataclass
class IndexMetadata:
    """Metadata describing the state of a built CSKS index."""

    version: str = "1.0"
    created_at: float = 0.0
    updated_at: float = 0.0
    entity_count: int = 0
    relationship_count: int = 0
    git_commit: str = ""
    indexed_files: list[str] = field(default_factory=list)
    file_hashes: dict[str, str] = field(default_factory=dict)


class CSKSIndexer:
    """Builds and exposes the CSKS knowledge index.

    M1.22: the index is built fully on startup. Incremental,
    diff-aware updates are deferred to M1.23.
    """

    def __init__(self, repo_root: Path, index_dir: Path | None = None) -> None:
        self.repo_root = repo_root
        self.index_dir = index_dir or (repo_root / ".csks-index")
        self.index_dir.mkdir(exist_ok=True)
        self._metadata_path = self.index_dir / "metadata.json"

        self.graph: KnowledgeGraph | None = None
        self.query_engine: CSKSQueryEngine | None = None
        self._metadata = IndexMetadata()

    def build_full_index(self) -> KnowledgeGraph:
        """Extract every source and build the complete knowledge graph."""
        start_time = time.time()

        orchestrator = CSKSExtractorOrchestrator(self.repo_root)
        entities, relationships = orchestrator.extract_all()

        graph = CSKSKnowledgeGraphBuilder().build(entities, relationships)
        self.graph = graph
        self.query_engine = CSKSQueryEngine(graph)

        self._metadata = IndexMetadata(
            version="1.0",
            created_at=time.time() if self._metadata.created_at == 0 else self._metadata.created_at,
            updated_at=time.time(),
            entity_count=graph.node_count,
            relationship_count=graph.edge_count,
            git_commit=self._get_git_commit(),
            indexed_files=self._get_indexed_files(),
            file_hashes=self._compute_file_hashes(),
        )
        self._save_metadata()
        self._elapsed_ms = int((time.time() - start_time) * 1000)
        return graph

    def get_graph(self) -> KnowledgeGraph:
        if self.graph is None:
            self.build_full_index()
        return self.graph

    def get_query_engine(self) -> CSKSQueryEngine:
        if self.query_engine is None:
            self.get_graph()
        return self.query_engine

    def get_entity(self, entity_id: str) -> dict | None:
        """Return a single entity with its relationships, or None."""
        graph = self.get_graph()
        node = graph.nodes.get(entity_id)
        if node is None:
            return None

        outgoing = [e for e in graph.edges if e.source_id == entity_id]
        incoming = [e for e in graph.edges if e.target_id == entity_id]

        return {
            "id": node.id,
            "type": node.type,
            "label": node.label,
            "properties": node.properties,
            "outgoing_relationships": [
                {"type": e.type, "target": e.target_id, "properties": e.properties}
                for e in outgoing
            ],
            "incoming_relationships": [
                {"type": e.type, "source": e.source_id, "properties": e.properties}
                for e in incoming
            ],
        }

    def search(self, entity_type: str | None = None, domain: str | None = None, limit: int = 50) -> list[dict]:
        """Faceted search over indexed entities."""
        graph = self.get_graph()
        results = []
        for node in graph.nodes.values():
            if entity_type and node.type != entity_type:
                continue
            if domain and node.properties.get("domain") != domain:
                continue
            results.append({
                "id": node.id,
                "type": node.type,
                "label": node.label,
                "properties": node.properties,
            })
            if len(results) >= limit:
                break
        return results

    def get_status(self) -> dict:
        """Return index status for the /csks/status endpoint."""
        graph = self.get_graph()
        return {
            "status": "ready",
            "entity_count": graph.node_count,
            "relationship_count": graph.edge_count,
            "git_commit": self._metadata.git_commit,
            "indexed_files": len(self._metadata.indexed_files),
            "last_build_ms": getattr(self, "_elapsed_ms", 0),
            "created_at": self._metadata.created_at,
            "updated_at": self._metadata.updated_at,
        }

    def incremental_update(self, changed_files: list[str]) -> KnowledgeGraph:
        """M1.23 stub: for M1.22 this rebuilds the full index."""
        return self.build_full_index()

    def _get_git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _get_indexed_files(self) -> list[str]:
        files: set[str] = set()
        for pattern in ("*.py", "*.md", "*.schema.json", "*.toml", "*.yaml", "*.yml", ".env*"):
            for path in self.repo_root.rglob(pattern):
                rel = str(path.relative_to(self.repo_root)).replace("\\", "/")
                parts = rel.split("/")
                if ".git" in parts or ".csks-index" in parts or "__pycache__" in parts or ".venv" in parts or "node_modules" in parts:
                    continue
                files.add(rel)
        return sorted(files)

    def _compute_file_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for rel in self._get_indexed_files():
            path = self.repo_root / rel
            try:
                hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            except OSError:
                continue
        return hashes

    def _save_metadata(self) -> None:
        payload = {
            "version": self._metadata.version,
            "created_at": self._metadata.created_at,
            "updated_at": self._metadata.updated_at,
            "entity_count": self._metadata.entity_count,
            "relationship_count": self._metadata.relationship_count,
            "git_commit": self._metadata.git_commit,
            "indexed_files": self._metadata.indexed_files,
            "file_hashes": self._metadata.file_hashes,
        }
        (self._metadata_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
