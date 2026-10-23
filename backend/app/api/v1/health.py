from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import get_es
from app.config import get_settings
from app.repositories import pg_repo

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Used by the frontend on open (status dot) and by Docker's healthcheck. No auth, no secrets."""
    s = get_settings()
    es = get_es()
    es_ok = es.ping()
    pg_ok = pg_repo.ping()
    chunks = 0
    if es_ok:
        try:
            chunks = es.count()
        except Exception:
            es_ok = False
    return {
        "status": "ok" if es_ok and pg_ok else "degraded",
        "elasticsearch": es_ok,
        "postgres": pg_ok,
        "gemini_configured": bool(s.gemini_api_key),
        "indexed_chunks": chunks,
        "models": {"llm": s.gemini_llm_model, "embedding": s.gemini_embedding_model, "dims": s.embedding_dimensions},
    }
