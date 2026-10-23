# 07 - Evaluating retrieval

"It feels better" is not engineering. Every RAG knob - chunk size, `k`, model, hybrid vs not - should be judged by numbers on a fixed question set.

## The test set

`sample_corpus/eval_questions.json` has 25 questions, each labelled with the file that contains the answer and a type:

| Type | Example | What it stresses |
|---|---|---|
| `keyword` | `Sputnik 1`, `TRAPPIST-1` | exact tokens -> BM25 territory |
| `semantic` | `Which robot flew a small aircraft on another planet?` | paraphrase, no shared words -> embeddings |
| `mixed` | `When did the Ingenuity helicopter first fly?` | both signals useful |

## Run it

```bash
docker compose exec backend python -m scripts.seed_corpus
docker compose exec backend python -m scripts.evaluate
```

It runs every question through `bm25`, `vector` and `hybrid` (RRF) and prints a table.

## The metrics

For each question, look at the ranked chunks and find the **first chunk from a correct file**:

- **Hit@1** - fraction of questions where that chunk is ranked #1.
- **Hit@5** (= Recall@5 here, one relevant doc per question) - fraction where it is anywhere in the top 5. This is the ceiling for answer quality: a chunk that is not in the prompt cannot be used.
- **MRR** (Mean Reciprocal Rank) - average of `1/rank`: rank 1 -> 1.0, rank 2 -> 0.5, rank 3 -> 0.33, absent -> 0. Rewards putting the right chunk *high*, not just *present*.

Worked example, 3 questions with first-correct ranks `1, 3, absent`:
Hit@1 = 1/3 = 0.33, Hit@5 = 2/3 = 0.67, MRR = (1 + 0.333 + 0) / 3 = 0.44.

## What you should expect to see

| | keyword | semantic | mixed |
|---|---|---|---|
| bm25 | strong | weak | medium |
| vector | medium-strong | strong | strong |
| **hybrid** | **strong** | **strong** | **strong** |

The exact numbers depend on the embedding model, so run it yourself - and if your results *differ* from this table, that is a finding worth investigating, not a bug in the docs. Hybrid's real promise is **no catastrophic category**: each single retriever has a type of question where it collapses.

## Limits of this evaluation (be critical)

- **Tiny**: 25 questions on 10 short documents. Differences of one question (4 points) are noise.
- **Easy corpus**: with 38 chunks, top-5 is 13% of everything. Real corpora have 10^5+ chunks where retrieval is much harder.
- **File-level labels**: we check the file, not the exact chunk or sentence.
- **Retrieval only**: it says nothing about whether the LLM wrote a correct answer. Answer quality needs another layer: LLM-as-judge for faithfulness ("is every claim supported by the cited chunks?") and answer relevance, or human review.
- **Written by the same person who wrote the corpus** - the questions are cleaner than real user queries.

## Ideas to extend

1. Add 20 harder questions (multi-hop: *"Which telescope studies the planets found by Kepler?"*).
2. Add questions with **no answer in the corpus**; measure whether the bot refuses.
3. Try `RRF_K` = 1, 10, 60, 200 and see whether the table moves.
4. Add a cross-encoder re-ranker after RRF and measure Hit@1.
5. Log real user questions with thumbs up/down and turn the failures into new test cases - the most valuable test set is the one built from real failures.
