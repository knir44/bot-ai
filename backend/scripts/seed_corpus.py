"""Index the bundled Space Exploration corpus (idempotent - safe to run repeatedly).

    docker compose exec backend python -m scripts.seed_corpus
"""
from __future__ import annotations

from app.repositories.es_repo import EsRepository
from app.services.ingestion import ingest_sample_corpus


def main() -> None:
    es = EsRepository()
    es.ensure_index()
    for r in ingest_sample_corpus(es):
        print(f"{r['filename']:<20} {r['characters']:>6} chars -> {r['chunks']:>2} chunks  ({r['elapsed_ms']} ms)")
    print(f"\nIndex now holds {es.count()} chunks.")


if __name__ == "__main__":
    main()
