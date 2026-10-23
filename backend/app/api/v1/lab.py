"""RAG Lab: endpoints that exist purely so you can SEE retrieval working."""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_es, require_session
from app.config import get_settings
from app.core.security import ValidationError, sanitize_text
from app.services import embeddings, ingestion
from app.services.embeddings import EmbeddingError
from app.services.retrieval.explain import parse_bm25_explanation
from app.services.retrieval.hybrid import MODES, retrieve

router = APIRouter(prefix="/lab", tags=["lab"], dependencies=[Depends(require_session)])


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: str = "hybrid"  # bm25 | vector | hybrid
    explain: bool = False  # attach the per-term BM25 breakdown to every BM25 hit
    retrieve_k: Optional[int] = Field(default=None, ge=1, le=100)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    rrf_k: Optional[int] = Field(default=None, ge=0, le=1000)  # play with it: 0 vs 60 vs 1000


@router.post("/search")
def search(body: SearchIn) -> dict:
    """Run BM25, vector and RRF side by side on the same query."""
    s = get_settings()
    if body.mode not in MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {MODES}")
    try:
        query = sanitize_text(body.query, s.max_message_chars)
        result = retrieve(
            query,
            get_es(),
            body.mode,
            body.retrieve_k or s.retrieve_k,
            body.top_k or s.top_k,
            s.rrf_k if body.rrf_k is None else body.rrf_k,
            explain=body.explain,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    for hit in result["bm25"]:
        expl = hit.pop("explanation", None)
        if body.explain:
            hit["breakdown"] = parse_bm25_explanation(expl)
    return result


@router.get("/embedding-map")
def embedding_map(q: Optional[str] = Query(default=None, max_length=2000)) -> dict:
    """Project all chunk embeddings from 768-D down to 2-D with PCA so you can look at them.

    PCA finds the two directions along which the vectors vary the most and drops the rest.
    A lot of information is lost, so treat the picture as intuition ("related chunks cluster"),
    not as exact distances. If `q` is given, the query is embedded and projected into the same plane.
    """
    rows = get_es().scan_embeddings()
    if len(rows) < 3:
        return {"points": [], "query": None, "note": "Need at least 3 chunks. Load the sample corpus first."}
    matrix = np.asarray([r["embedding"] for r in rows], dtype=np.float32)
    mean = matrix.mean(axis=0)
    _, _, vt = np.linalg.svd(matrix - mean, full_matrices=False)
    axes = vt[:2].T  # (dims, 2)
    coords = (matrix - mean) @ axes

    query_point = None
    if q:
        try:
            qv = np.asarray(embeddings.embed_query(sanitize_text(q, get_settings().max_message_chars)), dtype=np.float32)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except EmbeddingError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        qc = (qv - mean) @ axes
        query_point = {"x": float(qc[0]), "y": float(qc[1])}

    return {
        "points": [
            {
                "chunk_id": r["chunk_id"],
                "filename": r["filename"],
                "chunk_index": r["chunk_index"],
                "snippet": r["snippet"],
                "x": float(c[0]),
                "y": float(c[1]),
            }
            for r, c in zip(rows, coords)
        ],
        "query": query_point,
    }


@router.post("/seed")
def seed() -> dict:
    """Index the bundled Space Exploration corpus (idempotent)."""
    try:
        return {"ingested": ingestion.ingest_sample_corpus(get_es())}
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/corpus")
def clear_corpus() -> dict:
    """Remove every chunk (start from scratch)."""
    get_es().delete_all()
    return {"cleared": True}
