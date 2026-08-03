"""CSKS API routes (M1.22).

Mounted into the main FastAPI app from ``api/main.py``. The router only
orchestrates; formatting is delegated to ``AnswerFormatter`` so the query
engine never renders output.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from .indexer import CSKSIndexer
from .query import AnswerFormatter


def _default_repo_root() -> Path:
    """Resolve the repository root relative to this package."""
    return Path(__file__).resolve().parents[2]


def build_csks_router(indexer: CSKSIndexer | None = None) -> APIRouter:
    """Create the CSKS router with a lazily-built indexer.

    ``indexer`` may be provided for tests; otherwise an indexer is built
    against the repository root when the first route is hit.
    """
    router = APIRouter(prefix="/csks", tags=["csks"])
    state: dict = {"indexer": indexer}

    def _get_indexer() -> CSKSIndexer:
        if state["indexer"] is None:
            state["indexer"] = CSKSIndexer(_default_repo_root())
            state["indexer"].build_full_index()
        return state["indexer"]

    @router.get("/status")
    def csks_status() -> dict:
        """Return the CSKS index status."""
        return _get_indexer().get_status()

    @router.get("/query")
    def csks_query(q: str = Query(..., description="Natural-language question.")) -> dict:
        """Answer a question against the repository knowledge graph."""
        result = _get_indexer().get_query_engine().query(q)
        return AnswerFormatter.format_json(result)

    @router.get("/entity/{entity_id}")
    def csks_entity(entity_id: str) -> dict:
        """Return a single entity with its relationships."""
        details = _get_indexer().get_entity(entity_id)
        if details is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        return details

    @router.get("/search")
    def csks_search(
        q: str | None = Query(None, description="Search term for grouped results."),
        entity_type: str | None = Query(None, alias="type"),
        domain: str | None = Query(None),
        limit: int = Query(50, ge=1, le=500),
    ) -> dict:
        """Search the knowledge graph.

        With ``q``, returns grouped results across entity types. Without ``q``,
        returns faceted results filtered by ``type``/``domain`` (M1.22 behavior).
        """
        if q:
            from .search import grouped_search

            groups = grouped_search(_get_indexer().get_graph(), q, limit=limit)
            return {"groups": groups["groups"], "total": groups["total"]}
        results = _get_indexer().search(entity_type=entity_type, domain=domain, limit=limit)
        return {"results": results, "count": len(results)}

    return router


CSKS_ROUTER = build_csks_router()
