# 04 - TF-IDF and BM25: keyword relevance

Before embeddings, search engines ranked documents by **words**. That is still the best tool for names, numbers and rare terms - and it is what Elasticsearch does by default.

## Step 1 - The inverted index

Like the index at the back of a book: for every *term*, a list of the chunks containing it.

```
"perseverance" -> [mars_rovers#2]
"helicopter"   -> [mars_rovers#3]
"mars"         -> [mars_rovers#0, #1, #2, #3, voyager#1, ...]
```

Finding all chunks with "perseverance" is a dictionary lookup, not a scan of every chunk. Before indexing, text goes through an **analyzer** (we use Elasticsearch's `english` one): lowercase -> drop stop words ("the", "of") -> **stem** ("landing", "landed", "lands" -> `land`). The *query* goes through the same analyzer, so `Landing` matches `landed`.

## Step 2 - TF-IDF

Two intuitions multiplied together:

- **TF (term frequency)** - a chunk that mentions "oxygen" 5 times is probably more about oxygen than one that mentions it once.
- **IDF (inverse document frequency)** - a word that appears in *every* chunk ("apollo" in a space corpus) tells you nothing; a word in one chunk ("Swigert") tells you a lot.

```
tfidf(t, d) = tf(t, d) * idf(t)          idf(t) = log( N / df(t) )
```

`N` = number of chunks, `df(t)` = number of chunks containing `t`. If a term is in all chunks, `idf = log(1) = 0` - it contributes nothing, automatically acting like a stop word.

Run the from-scratch implementation:

```bash
docker compose exec backend python -m app.services.retrieval.tfidf_demo
```

## Step 3 - BM25: TF-IDF with two fixes

BM25 ("Best Match 25") is the formula Lucene/Elasticsearch use. For each query term:

```
                          tf
score(t, d) = idf(t) * -------------------------------------
                       tf + k1 * (1 - b + b * (dl / avgdl))
```

with Lucene's `idf(t) = ln(1 + (N - n + 0.5) / (n + 0.5))` where `n` = chunks containing `t`. The chunk's score is the **sum over query terms**.

### Fix 1: saturation (the `k1` knob)

Plain TF says 20 mentions is 20x better than 1. Intuitively the 20th mention adds almost nothing. With `k1 = 1.2` and an average-length chunk:

| tf | 1 | 2 | 3 | 5 | 10 | 20 | 100 |
|---|---|---|---|---|---|---|---|
| tf / (tf + 1.2) | 0.455 | 0.625 | 0.714 | 0.806 | 0.893 | 0.943 | 0.988 |

It climbs fast, then flattens toward 1. Keyword-stuffing a chunk cannot dominate. Larger `k1` = slower saturation.

### Fix 2: length normalisation (the `b` knob)

A match in a 20-word chunk is more meaningful than in a 2000-word one (long chunks mention everything eventually). `dl/avgdl` compares this chunk's length to the average. For `tf = 2`:

| chunk length vs average | 0.5x (short) | 1x | 2x (long) |
|---|---|---|---|
| tf part | 0.727 | 0.625 | 0.488 |

`b = 0.75` applies 75% of the penalty; `b = 0` ignores length; `b = 1` is full normalisation.

### Why IDF matters - real numbers

For a 38-chunk corpus like ours:

| Term appears in n chunks | idf |
|---|---|
| 1 ("swigert") | 3.26 |
| 4 | 2.16 |
| 30 ("the"-like) | 0.25 |

So a query `Apollo 13 oxygen tank explosion` is decided mostly by `13`, `oxygen`, `explosion` (rare), while `apollo` (in many chunks) only nudges.

## Where BM25 fails

- **Vocabulary mismatch**: `"red planet robot"` shares no stemmed token with a chunk that says `"Perseverance rover on Mars"`. Score: 0. -> embeddings ([03](03-embeddings.md)).
- **No word order / meaning**: "dog bites man" = "man bites dog".
- **Typos** (without fuzziness enabled).

## See it for yourself

In the Lab, search `Apollo 13 oxygen tank explosion` and open **Why this BM25 score?** on the top hit. It shows, per term: raw `freq`, `n / N`, `idf`, the saturated `tf part`, and their product - the same formula above filled in by Elasticsearch's `explain` API. (`backend/app/services/retrieval/explain.py` parses that response; `tests/test_tfidf_bm25.py` checks our hand formula.)

Note the term column is **stemmed** (`landed` -> `land`): that is the analyzer from Step 1 at work.
