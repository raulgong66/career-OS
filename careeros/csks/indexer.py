from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from careeros.knowledge import KnowledgeGraph

from .builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from .models import ExtractedEntity, ExtractedRelationship
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

    M1.22: the index is built fully on startup. M1.27: ``incremental_update``
    performs a git-diff/hash-aware partial rebuild that re-extracts only the
    changed source files, reusing the persisted per-source extraction artifacts
    (``.csks-index/sources/*.json``) for unchanged files. Deterministic, no LLM.
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
        """Extract every source and build the complete knowledge graph.

        Also persists per-source extraction artifacts so a later
        ``incremental_update`` can re-use them for unchanged files.
        """
        start_time = time.time()

        orchestrator = CSKSExtractorOrchestrator(self.repo_root)
        entities: list = []
        relationships: list = []
        for source_path in orchestrator.discover_source_paths():
            source_entities, source_relationships = orchestrator.extract_all([source_path])
            entities.extend(source_entities)
            relationships.extend(source_relationships)
            self._write_artifact(source_path, source_entities, source_relationships)
        self._prune_artifacts(orchestrator.discover_source_paths())

        graph = CSKSKnowledgeGraphBuilder().build(entities, relationships)
        self.graph = graph
        self.query_engine = CSKSQueryEngine(graph, repo_root=self.repo_root)

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
        """Re-index only the changed source files.

        Changed files are derived from the explicit ``changed_files`` list, the
        working-tree git diff (when available), and a persisted file-hash
        comparison. Changed files are re-extracted; unchanged files reuse their
        persisted extraction artifacts. The graph is rebuilt deterministically
        so the result is identical to a full rebuild of the same repo state.

        On the first index (no persisted artifacts) this falls back to a full
        build to establish the baseline.
        """
        start_time = time.time()
        self._load_metadata()
        orchestrator = CSKSExtractorOrchestrator(self.repo_root)
        source_paths = orchestrator.discover_source_paths()

        if not self._has_artifacts():
            return self.build_full_index()

        for rel in self._detect_changed_files(changed_files):
            if not self._is_indexable(rel, orchestrator):
                continue
            if (self.repo_root / rel).is_file():
                source_entities, source_relationships = orchestrator.extract_all([rel])
                self._write_artifact(rel, source_entities, source_relationships)
            else:
                self._remove_artifact(rel)

        graph = self._build_graph_from_cache(orchestrator, source_paths)
        self.graph = graph
        self.query_engine = CSKSQueryEngine(graph, repo_root=self.repo_root)

        self._metadata = IndexMetadata(
            version="1.0",
            created_at=self._metadata.created_at,
            updated_at=time.time(),
            entity_count=graph.node_count,
            relationship_count=graph.edge_count,
            git_commit=self._get_git_commit(),
            indexed_files=self._get_indexed_files(),
            file_hashes=self._compute_file_hashes(),
        )
        self._prune_artifacts(source_paths)
        self._save_metadata()
        self._elapsed_ms = int((time.time() - start_time) * 1000)
        return graph

    # -- git / change detection ----------------------------------------------

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

    def _git_changed_files(self) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _detect_changed_files(self, changed_files: list[str]) -> list[str]:
        """Return the sorted, de-duplicated set of changed source paths."""
        changed: set[str] = set()
        for path in changed_files:
            rel = self._normalize_rel(path)
            if rel:
                changed.add(rel)
        changed.update(self._git_changed_files())

        current_hashes = self._compute_file_hashes()
        prior_hashes = self._metadata.file_hashes
        for rel, digest in current_hashes.items():
            if prior_hashes.get(rel) != digest:
                changed.add(rel)
        for rel in prior_hashes:
            if rel not in current_hashes:
                changed.add(rel)
        return sorted(changed)

    @staticmethod
    def _normalize_rel(path: str) -> str:
        return path.replace("\\", "/")

    @staticmethod
    def _is_indexable(rel: str, orchestrator: CSKSExtractorOrchestrator) -> bool:
        return any(extractor.can_extract(rel) for extractor in orchestrator.extractors)

    # -- file listing / hashing ----------------------------------------------

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

    # -- persisted per-source artifacts ---------------------------------------

    def _artifact_path(self, rel: str) -> Path:
        digest = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:24]
        return self.index_dir / "sources" / f"{digest}.json"

    def _has_artifacts(self) -> bool:
        sources_dir = self.index_dir / "sources"
        if not sources_dir.is_dir():
            return False
        return any(sources_dir.iterdir())

    def _write_artifact(self, rel: str, entities: list, relationships: list) -> None:
        payload = {
            "path": rel,
            "entities": [asdict(e) for e in entities],
            "relationships": [asdict(r) for r in relationships],
        }
        path = self._artifact_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_artifact(self, rel: str) -> tuple[list, list] | None:
        path = self._artifact_path(rel)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        entities = [ExtractedEntity(**item) for item in payload.get("entities", [])]
        relationships = [ExtractedRelationship(**item) for item in payload.get("relationships", [])]
        return entities, relationships

    def _remove_artifact(self, rel: str) -> None:
        path = self._artifact_path(rel)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    def _prune_artifacts(self, source_paths: list[str]) -> None:
        current = {self._artifact_path(rel) for rel in source_paths}
        sources_dir = self.index_dir / "sources"
        if not sources_dir.is_dir():
            return
        for path in sources_dir.glob("*.json"):
            if path not in current:
                try:
                    path.unlink()
                except OSError:
                    pass

    def _build_graph_from_cache(self, orchestrator: CSKSExtractorOrchestrator, source_paths: list[str]) -> KnowledgeGraph:
        """Rebuild the graph from persisted artifacts in canonical source order.

        The graph is constructed through the same builder and the same source
        order as ``build_full_index`` so the result is exactly equivalent to a
        full rebuild of the current repository state.
        """
        entities: list = []
        relationships: list = []
        for source_path in source_paths:
            cached = self._read_artifact(source_path)
            if cached is not None:
                source_entities, source_relationships = cached
            else:
                source_entities, source_relationships = orchestrator.extract_all([source_path])
                self._write_artifact(source_path, source_entities, source_relationships)
            entities.extend(source_entities)
            relationships.extend(source_relationships)
        return CSKSKnowledgeGraphBuilder().build(entities, relationships)

    # -- metadata persistence --------------------------------------------------

    def _load_metadata(self) -> None:
        if not self._metadata_path.exists():
            return
        try:
            payload = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self._metadata = IndexMetadata(
            version=payload.get("version", "1.0"),
            created_at=payload.get("created_at", 0.0),
            updated_at=payload.get("updated_at", 0.0),
            entity_count=payload.get("entity_count", 0),
            relationship_count=payload.get("relationship_count", 0),
            git_commit=payload.get("git_commit", ""),
            indexed_files=payload.get("indexed_files", []),
            file_hashes=payload.get("file_hashes", {}),
        )

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
