"""Hybrid retrieval = BM25 + vector search, fused with RRF.

                    +--> BM25 (ES `match`, inverted index)  --> ranked list 1 --+
   user question ---+                                                            +--> RRF --> top_k
                    +--> embed -> kNN (ES dense_vector)     --> ranked list 2 --+

WHY BOTH?   They fail in opposite ways:
  * BM25 is exact: finds "Apollo 13" or an error code perfectly, but misses synonyms
    ("the red planet" will not match a chunk that only says "Mars").
  * Embeddings are fuzzy: understand paraphrase and intent, but can blur exact names/numbers
    ("Apollo 11" and "Apollo 13" have very similar vectors!).
  Fusing them covers both weaknesses - the standard production recipe.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from app.repositories.es_repo import EsRepository
from app.services import embeddings
from app.services.retrieval.rrf import rrf_fuse

MODES = ("bm25", "vector", "hybrid")


def _rank(hits: List[dict]) -> List[dict]:
    return [{**h, "rank": i + 1} for i, h in enumerate(hits)]


def retrieve(
    query: str,
    es: EsRepository,
    mode: str = "hybrid",
    retrieve_k: int = 20,
    top_k: int = 5,
    rrf_k: int = 60,
    explain: bool = False,
) -> Dict:
    """Run the retrievers selected by `mode` and fuse them. Returns everything needed to explain the result."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    timings: Dict[str, float] = {}
    bm25_hits: List[dict] = []
    vector_hits: List[dict] = []

    if mode in ("bm25", "hybrid"):
        t = time.perf_counter()
        bm25_hits = _rank(es.bm25_search(query, retrieve_k, explain=explain))
        timings["bm25_ms"] = round((time.perf_counter() - t) * 1000, 1)

    if mode in ("vector", "hybrid"):
        t = time.perf_counter()
        qvec = embeddings.embed_query(query)
        timings["embed_query_ms"] = round((time.perf_counter() - t) * 1000, 1)
        t = time.perf_counter()
        vector_hits = _rank(es.knn_search(qvec, retrieve_k))
        timings["knn_ms"] = round((time.perf_counter() - t) * 1000, 1)

    # --- fusion (with a single retriever this just preserves its order)
    rankings = {}
    if bm25_hits:
        rankings["bm25"] = [h["chunk_id"] for h in bm25_hits]
    if vector_hits:
        rankings["vector"] = [h["chunk_id"] for h in vector_hits]
    by_id = {h["chunk_id"]: h for h in vector_hits}
    by_id.update({h["chunk_id"]: {**by_id.get(h["chunk_id"], {}), **h} for h in bm25_hits})
    bm25_score = {h["chunk_id"]: h["score"] for h in bm25_hits}
    vector_score = {h["chunk_id"]: h["score"] for h in vector_hits}

    fused = []
    for entry in rrf_fuse(rankings, k=rrf_k)[:top_k]:
        cid = entry["id"]
        base = {k: v for k, v in by_id[cid].items() if k not in ("score", "rank", "explanation")}
        fused.append(
            {
                **base,
                "rrf_score": entry["score"],
                "contributions": entry["contributions"],
                "bm25_score": bm25_score.get(cid),
                "vector_score": vector_score.get(cid),
            }
        )

    return {
        "query": query,
        "mode": mode,
        "params": {"retrieve_k": retrieve_k, "top_k": top_k, "rrf_k": rrf_k},
        "bm25": bm25_hits,
        "vector": vector_hits,
        "fused": fused,
        "timings_ms": timings,
    }


def slim(hit: dict, chars: int = 220) -> dict:
    """Shrink a hit for storage in the chat trace (full text lives in ES; trace needs only a preview)."""
    return {
        "chunk_id": hit["chunk_id"],
        "filename": hit["filename"],
        "chunk_index": hit["chunk_index"],
        "snippet": hit["content"][:chars],
        **{k: hit[k] for k in ("score", "rank", "rrf_score", "contributions", "bm25_score", "vector_score") if k in hit},
    }
