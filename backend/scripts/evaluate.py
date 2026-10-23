"""Measure retrieval quality: BM25 vs vector vs hybrid (RRF).

Run inside the backend container, after loading the corpus:
    docker compose exec backend python -m scripts.seed_corpus
    docker compose exec backend python -m scripts.evaluate

For each question in sample_corpus/eval_questions.json we know which file contains the answer.
We run the same question through each retrieval mode and check where the right file shows up.

Metrics (averaged over questions):
  Hit@1  - was the very first chunk from a correct file?
  Hit@5  - was ANY of the top 5 chunks from a correct file?  (a.k.a. Recall@5 with one relevant doc)
  MRR    - Mean Reciprocal Rank: 1/rank of the first correct chunk (1.0 if first, 0.5 if second, 0 if absent).
           Rewards putting the right chunk near the top, not just somewhere in the top 5.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from app.config import get_settings
from app.repositories.es_repo import EsRepository
from app.services.retrieval.hybrid import MODES, retrieve

TOP_K = 5


def score_question(fused: list, expected: list) -> tuple:
    for rank, hit in enumerate(fused, start=1):
        if hit["filename"] in expected:
            return rank, 1.0 / rank
    return None, 0.0


def main() -> int:
    s = get_settings()
    es = EsRepository()
    if es.count() == 0:
        print("The index is empty. Run:  python -m scripts.seed_corpus")
        return 1

    questions = json.loads((Path(s.sample_corpus_dir) / "eval_questions.json").read_text(encoding="utf-8"))
    # stats[mode][qtype] = list of (first_correct_rank or None, reciprocal_rank)
    stats = {m: defaultdict(list) for m in MODES}
    misses = defaultdict(list)

    for q in questions:
        for mode in MODES:
            result = retrieve(q["question"], es, mode, s.retrieve_k, TOP_K, s.rrf_k)
            rank, rr = score_question(result["fused"], q["expected"])
            stats[mode][q["type"]].append((rank, rr))
            stats[mode]["ALL"].append((rank, rr))
            if rank is None:
                misses[mode].append(q["question"])

    print(f"\nRetrieval evaluation - {len(questions)} questions, top_k={TOP_K}, rrf_k={s.rrf_k}\n")
    print(f"{'type':<10}{'mode':<9}{'Hit@1':>8}{'Hit@5':>8}{'MRR':>8}")
    print("-" * 43)
    for qtype in ("keyword", "semantic", "mixed", "ALL"):
        for mode in MODES:
            rows = stats[mode][qtype]
            n = len(rows)
            hit1 = sum(1 for r, _ in rows if r == 1) / n
            hit5 = sum(1 for r, _ in rows if r is not None) / n
            mrr = sum(rr for _, rr in rows) / n
            print(f"{qtype:<10}{mode:<9}{hit1:>8.2f}{hit5:>8.2f}{mrr:>8.2f}")
        print()

    for mode in MODES:
        if misses[mode]:
            print(f"[{mode}] missed entirely (not in top {TOP_K}):")
            for question in misses[mode]:
                print(f"   - {question}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
