"""Reciprocal Rank Fusion (RRF) - Cormack, Clarke & Buettcher, SIGIR 2009.

THE PROBLEM
  BM25 scores look like 11.3, 8.7, 2.1 ...  (unbounded, depends on corpus statistics)
  Vector scores look like 0.83, 0.79, 0.71 (cosine similarity, bounded)
  You cannot add or average these numbers - they live on different scales.

THE TRICK
  Throw the scores away and use only the RANK (1st, 2nd, 3rd...) in each list:

        RRF(d) = sum over every ranked list L of   1 / (k + rank_L(d))

  A chunk ranked high by *both* retrievers collects two big contributions and floats to the top.
  A chunk that only one retriever found still gets points from that one list.

WHY k = 60?
  k dampens the gap between the top ranks. With k=0, rank 1 (1.0) is worth twice rank 2 (0.5).
  With k=60, rank 1 = 1/61 = 0.01639 and rank 2 = 1/62 = 0.01613 - nearly equal, so one
  retriever's #1 pick cannot single-handedly dominate. 60 is the value the paper found robust.

WORKED EXAMPLE (k=60)
      BM25 list:   A, B, C        vector list:  C, A, D
      A: 1/(60+1) + 1/(60+2) = 0.01639 + 0.01613 = 0.03252   <- found by both, high in both
      C: 1/(60+3) + 1/(60+1) = 0.01587 + 0.01639 = 0.03226
      B: 1/(60+2)            = 0.01613                       <- BM25 only
      D: 1/(60+3)            = 0.01587                       <- vector only
      Fused order: A, C, B, D
"""
from __future__ import annotations

from typing import Dict, List


def rrf_fuse(rankings: Dict[str, List[str]], k: int = 60) -> List[dict]:
    """Fuse several ranked lists of ids.

    `rankings` maps a retriever name to its ids, best first, e.g. {"bm25": [...], "vector": [...]}.
    Returns one dict per id, best first:
        {"id": ..., "score": float, "contributions": {name: {"rank": int, "score": float}}}
    The per-list `contributions` are what the UI shows to explain *why* a chunk won.
    """
    fused: Dict[str, dict] = {}
    for name, ids in rankings.items():
        for position, doc_id in enumerate(ids):
            rank = position + 1  # ranks are 1-based
            part = 1.0 / (k + rank)
            entry = fused.setdefault(doc_id, {"id": doc_id, "score": 0.0, "contributions": {}})
            entry["score"] += part
            entry["contributions"][name] = {"rank": rank, "score": part}
    # Ties (same score) are broken by id so the output is deterministic.
    return sorted(fused.values(), key=lambda e: (-e["score"], e["id"]))
