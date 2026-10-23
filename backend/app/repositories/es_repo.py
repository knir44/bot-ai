"""Elasticsearch repository: the knowledge store.

ONE index, TWO ways to search it:
  * `content`   - analyzed text  -> inverted index -> BM25 (keyword relevance)
  * `embedding` - dense_vector   -> HNSW graph     -> kNN  (semantic relevance)

INVERTED INDEX (what makes BM25 fast)
  Like the index at the back of a book: for each *term* a list of the chunks containing it.
      "perseverance" -> [chunk 12]      "mars" -> [chunk 3, 12, 14, 15]
  The `english` analyzer first lowercases, removes stop words and STEMS ("landing" -> "land").
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Iterable, List, Optional

from elasticsearch import Elasticsearch, helpers

from app.config import get_settings

log = logging.getLogger(__name__)

_SOURCE_EXCLUDES = ["embedding"]  # never ship 768 floats back to the client


class EsRepository:
    def __init__(self) -> None:
        s = get_settings()
        self.index = s.es_index
        self.dims = s.embedding_dimensions
        self.es = Elasticsearch(s.elasticsearch_url, request_timeout=30)

    # ------------------------------------------------------------------ setup
    def ping(self) -> bool:
        try:
            return bool(self.es.ping())
        except Exception:
            return False

    def ensure_index(self, retries: int = 30) -> None:
        for attempt in range(retries):
            if self.ping():
                break
            log.info("Waiting for Elasticsearch (%d/%d)...", attempt + 1, retries)
            time.sleep(2)
        if self.es.indices.exists(index=self.index):
            return
        self.es.indices.create(
            index=self.index,
            settings={"number_of_shards": 1, "number_of_replicas": 0},
            mappings={
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "filename": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "content": {"type": "text", "analyzer": "english"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.dims,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        )
        log.info("Created index %s (dims=%d)", self.index, self.dims)

    # ------------------------------------------------------------------ write
    def index_chunks(self, doc_id: str, filename: str, chunks: List[str], embeddings: List[List[float]]) -> int:
        self.delete_document(doc_id)  # re-uploading the same file replaces it
        actions = (
            {
                "_index": self.index,
                "_id": f"{doc_id}:{i}",
                "_source": {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "content": text,
                    "embedding": vec,
                },
            }
            for i, (text, vec) in enumerate(zip(chunks, embeddings))
        )
        ok, _ = helpers.bulk(self.es, actions, refresh="wait_for")
        return ok

    def delete_document(self, doc_id: str) -> int:
        resp = self.es.delete_by_query(index=self.index, query={"term": {"doc_id": doc_id}}, refresh=True)
        return resp.get("deleted", 0)

    def delete_all(self) -> None:
        self.es.delete_by_query(index=self.index, query={"match_all": {}}, refresh=True)

    # ------------------------------------------------------------------ read
    def count(self) -> int:
        return self.es.count(index=self.index)["count"]

    def list_documents(self) -> List[dict]:
        resp = self.es.search(
            index=self.index,
            size=0,
            aggs={
                "docs": {
                    "terms": {"field": "doc_id", "size": 500},
                    "aggs": {"first": {"top_hits": {"size": 1, "_source": ["filename"]}}},
                }
            },
        )
        return [
            {
                "doc_id": b["key"],
                "filename": b["first"]["hits"]["hits"][0]["_source"]["filename"],
                "chunks": b["doc_count"],
            }
            for b in resp["aggregations"]["docs"]["buckets"]
        ]

    @staticmethod
    def _hit(h: dict, score: float) -> dict:
        src = h["_source"]
        return {
            "chunk_id": h["_id"],
            "doc_id": src["doc_id"],
            "filename": src["filename"],
            "chunk_index": src["chunk_index"],
            "content": src["content"],
            "score": score,
        }

    def bm25_search(self, query: str, size: int, explain: bool = False) -> List[dict]:
        """Keyword search. `match` analyzes the query with the SAME analyzer as the index, then scores with BM25."""
        resp = self.es.search(
            index=self.index,
            query={"match": {"content": {"query": query}}},
            size=size,
            explain=explain,
            source_excludes=_SOURCE_EXCLUDES,
        )
        hits = []
        for h in resp["hits"]["hits"]:
            hit = self._hit(h, h["_score"])
            if explain:
                hit["explanation"] = h.get("_explanation")
            hits.append(hit)
        return hits

    def knn_search(self, vector: List[float], size: int) -> List[dict]:
        """Semantic search: approximate nearest neighbours by cosine similarity (HNSW graph)."""
        resp = self.es.search(
            index=self.index,
            knn={
                "field": "embedding",
                "query_vector": vector,
                "k": size,
                "num_candidates": max(size * 5, 100),  # candidates examined per shard: higher = better recall, slower
            },
            size=size,
            source_excludes=_SOURCE_EXCLUDES,
        )
        # ES maps cosine into a positive score: _score = (1 + cos) / 2. Undo it so humans see the real cosine.
        return [self._hit(h, 2.0 * h["_score"] - 1.0) for h in resp["hits"]["hits"]]

    def scan_embeddings(self, limit: int = 2000) -> List[dict]:
        out: List[dict] = []
        for h in helpers.scan(
            self.es,
            index=self.index,
            query={"query": {"match_all": {}}},
            _source=["embedding", "filename", "chunk_index", "content"],
        ):
            src = h["_source"]
            out.append(
                {
                    "chunk_id": h["_id"],
                    "filename": src["filename"],
                    "chunk_index": src["chunk_index"],
                    "snippet": src["content"][:160],
                    "embedding": src["embedding"],
                }
            )
            if len(out) >= limit:
                break
        return out
