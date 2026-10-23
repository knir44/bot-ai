# 05 - Hybrid search and Reciprocal Rank Fusion (RRF)

## Why combine two retrievers?

They fail in opposite ways:

| Query | BM25 (keywords) | Vector (meaning) |
|---|---|---|
| `Lovell Swigert Haise` (names) | finds it instantly | may drift to other crew lists |
| `Which robot flew a small aircraft on another planet?` | 0 matching words -> miss | finds `Ingenuity helicopter` |
| `TRAPPIST-1` (rare token) | exact hit | embedding of a rare token is unreliable |
| `Which flight nearly ended in disaster?` | weak | finds Apollo 13 |

Hybrid search runs both and merges. It is the standard production recipe.

## The merging problem

BM25 scores look like `11.3, 8.7, 2.1` - unbounded, dependent on corpus statistics and query length.
Cosine scores look like `0.83, 0.79, 0.71` - bounded and tightly packed.

You **cannot** add or average these. Two bad fixes people try:

1. *Normalise then weighted-sum* (`0.5*bm25_norm + 0.5*cos`): needs a magic weight, and min-max normalisation is distorted by outliers and changes per query.
2. *Take the max*: one retriever always wins.

## RRF: ignore the scores, use only the ranks

Cormack, Clarke & Buettcher, 2009:

```
RRF(d) = Σ over lists L  of   1 / (k + rank_L(d))          k = 60
```

Worked example. BM25 returns `A, B, C`; vector search returns `C, A, D`:

| chunk | BM25 rank | vector rank | contribution(s) | RRF score |
|---|---|---|---|---|
| **A** | 1 | 2 | 1/61 + 1/62 = 0.01639 + 0.01613 | **0.03252** |
| **C** | 3 | 1 | 1/63 + 1/61 = 0.01587 + 0.01639 | **0.03226** |
| B | 2 | - | 1/62 | 0.01613 |
| D | - | 3 | 1/63 | 0.01587 |

Final order: **A, C, B, D**. A and C - which *both* retrievers liked - beat B and D, which only one liked. No weights, no normalisation, works with any number of lists.

The whole implementation is ~15 lines: [`rrf.py`](../backend/app/services/retrieval/rrf.py).

## What does `k` do?

`k` flattens the curve at the top:

| rank | 1 | 2 | 3 | 10 | 20 |
|---|---|---|---|---|---|
| k = 0 → 1/rank | 1.000 | 0.500 | 0.333 | 0.100 | 0.050 |
| k = 60 → 1/(60+rank) | 0.01639 | 0.01613 | 0.01587 | 0.01429 | 0.01250 |

- **k = 0**: rank 1 is worth *twice* rank 2 - one retriever's single #1 pick can beat chunks both retrievers placed #2.
- **k = 60**: ranks 1 and 2 are nearly equal; what matters is *appearing in several lists*. 60 is the paper's empirically robust value.
- Large k (e.g. 1000): almost everything scores the same; ranking is dominated by who appears in more lists.

**Try it:** in the Lab move the *RRF k* slider to 0 and search `Apollo 11 oxygen tank`, then to 60 and 200. Watch the RRF column reorder and read each chunk's contribution chips.

## Limitations (be honest about them)

- RRF throws away **confidence**: a BM25 score of 40 vs 4 is treated the same as ranks 1 vs 2. If one retriever is extremely sure, RRF doesn't know.
- It can only reorder what the retrievers returned: a chunk neither found (`RETRIEVE_K=20` each) is lost forever.
- It doesn't *understand* relevance. A **re-ranker** (a cross-encoder model that reads query and chunk together) is the usual next step: take the RRF top 20, re-score with the cross-encoder, keep 5.

## Elasticsearch has an `rrf` retriever - why not use it?

ES 8.14+ ships a native RRF retriever, but it requires a paid (Enterprise) licence tier. Implementing RRF yourself is trivial, free, and - for learning - lets you inspect every rank and contribution, which is exactly what the UI trace shows.

## Code path

```
retrieve()  (hybrid.py)
  ├─ es.bm25_search(query, 20)           -> ranked list 1
  ├─ embed_query() -> es.knn_search(20)  -> ranked list 2
  └─ rrf_fuse({"bm25": ids1, "vector": ids2}, k=60)[:top_k]
```
