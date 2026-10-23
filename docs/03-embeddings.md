# 03 - Embeddings

## The idea

An **embedding model** is a neural network that reads a text and outputs a fixed-length list of numbers - here **768** of them. Think of it as GPS coordinates for *meaning*: texts about similar things land at nearby coordinates, **even if they share no words.**

```
"Mars rover"                ->  [ 0.021, -0.113,  0.087, ... ]   (768 numbers)
"robot driving on the red planet" -> [ 0.019, -0.109,  0.091, ... ]   <- very close
"chocolate cake recipe"     ->  [-0.140,  0.052, -0.066, ... ]   <- far away
```

The individual numbers mean nothing to a human. Only **distances** between vectors matter.

## Cosine similarity

How do we measure "close"? By the **angle** between the two vectors:

```
                a · b            sum(a_i * b_i)
cos(a, b) = ------------- = ----------------------
              |a| * |b|     sqrt(sum a_i^2) * sqrt(sum b_i^2)
```

- `1.0` -> same direction (same meaning)
- `0.0` -> unrelated (perpendicular)
- `-1.0` -> opposite

Tiny 2-D example: `a = (3, 4)`, `b = (4, 3)`:  `a·b = 24`, `|a| = |b| = 5` -> cos = 24/25 = **0.96**. Very similar direction.

**Normalisation.** If every vector is scaled to length 1, the denominator is 1 and cosine becomes a plain dot product, which hardware does extremely fast. `embeddings.py` normalises every vector for this reason. (Elasticsearch's `cosine` similarity would also work on unnormalised data, but it needs to store extra values.)

> Elasticsearch reports cosine as `_score = (1 + cos) / 2` so scores stay positive. `es_repo.knn_search` converts it back so the UI shows the true cosine.

## Two kinds of text: query vs document

A question ("who first walked on the Moon?") looks nothing like the passage that answers it ("Armstrong stepped onto the surface first..."). Retrieval models are trained **asymmetrically** with task types:

| Task type | Used for |
|---|---|
| `RETRIEVAL_DOCUMENT` | chunks at indexing time |
| `RETRIEVAL_QUERY` | the user's question at search time |

Using the same type for both quietly lowers quality. See the two functions in `embeddings.py`.

## Dimensions and Matryoshka vectors

`gemini-embedding-001` natively produces 3072 numbers but was trained so that the **first n numbers are already a good embedding** (Matryoshka representation learning, like nesting dolls). We ask for 768:

| Dimensions | Storage per chunk (float32) | Quality |
|---|---|---|
| 3072 | 12 KB | best |
| 768 | 3 KB | slightly lower |
| 256 | 1 KB | noticeably lower |

Truncation breaks the unit length, so we re-normalise. **Changing `EMBEDDING_DIMENSIONS` (or the model) requires re-indexing** - vectors from different models/sizes live in unrelated spaces and cannot be compared. The index mapping fixes `dims`, so ES will refuse mismatched vectors rather than silently return garbage.

## Searching 768 dimensions fast: HNSW

Comparing the query with every chunk (brute force) is `O(n)`. Elasticsearch builds an **HNSW graph** (Hierarchical Navigable Small World): a multi-layer "road map" where each vector is linked to near neighbours. A search hops greedily from a coarse top layer down to a detailed bottom layer, visiting only a tiny fraction of the vectors. It is **approximate** (it may miss the true nearest neighbour) and `num_candidates` controls the recall/speed trade-off.

## What embeddings are bad at

- **Exact identifiers**: `Apollo 11` vs `Apollo 13` - almost the same meaning to a model, very different to you. Error codes, part numbers, names -> keyword search ([04](04-tfidf-bm25.md)).
- **Negation and numbers**: "not safe" and "safe" are near neighbours.
- **Out-of-domain jargon** the model never saw.
- They compress; they do not *understand*. A high cosine means "topically similar", not "answers the question".

## Try it in the Lab

1. Press **Plot chunks (+ my query)**. Chunks from the same file should cluster (PCA loses information, so it is only a rough picture).
2. Type `helicopter on Mars`, plot again: the ★ should land near the `mars_rovers.txt` dots.
3. Compare cosine values in the *Vector* column for a good question vs. nonsense like `purple monkey dishwasher`. Even nonsense gets a "nearest" result - **vector search always returns something**. That is why we need a "not found" instruction in the prompt ([06](06-grounded-prompting.md)).
