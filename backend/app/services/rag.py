"""The full RAG loop for one chat turn.

   question
      |  (follow-up? rewrite into a standalone question using chat history)
      v
   retrieve  ->  BM25 + vector -> RRF -> top_k chunks          [R = Retrieval]
      v
   augment   ->  paste chunks into a grounded prompt            [A = Augmented]
      v
   generate  ->  Gemini answers using only that context         [G = Generation]
      v
   save to Postgres: ONE row with question, answer, sources and the full trace
"""
from __future__ import annotations

import logging
import time
from typing import List

from app.config import get_settings
from app.repositories.es_repo import EsRepository
from app.repositories.pg_repo import PgRepository, turns_to_messages
from app.services import llm
from app.services.retrieval.hybrid import retrieve, slim

log = logging.getLogger(__name__)


class RagService:
    def __init__(self, es: EsRepository, pg: PgRepository):
        self.es, self.pg = es, pg

    def answer(self, session_id: str, question: str) -> dict:
        s = get_settings()
        timings = {}
        recent = turns_to_messages(self.pg.get_turns(session_id, s.history_turns))
        history = [{"role": m["role"], "content": m["content"]} for m in recent]

        # Nothing indexed (e.g. the sample corpus failed to load): do not block the user,
        # answer from the model's general knowledge and say so. This is NOT RAG - there is nothing to retrieve.
        if self.es.count() == 0:
            t = time.perf_counter()
            answer = llm.generate_general_answer(question, history)
            timings["llm_ms"] = round((time.perf_counter() - t) * 1000, 1)
            self.pg.add_turn(session_id, question, answer)
            return {"answer": answer, "sources": [], "trace": None}

        # 1. Condense follow-ups: "When did it launch?" is useless as a search query on its own.
        standalone = question
        if history and s.rewrite_followups:
            t = time.perf_counter()
            standalone = llm.rewrite_question(question, history) or question
            timings["rewrite_ms"] = round((time.perf_counter() - t) * 1000, 1)

        # 2. Retrieve
        result = retrieve(standalone, self.es, "hybrid", s.retrieve_k, s.top_k, s.rrf_k)
        timings.update(result["timings_ms"])

        # 3. Augment + 4. Generate
        chunks = result["fused"]
        prompt = llm.build_prompt(question if standalone == question else f"{question} (i.e. {standalone})", chunks, history)
        t = time.perf_counter()
        answer = llm.generate_answer(prompt)
        timings["llm_ms"] = round((time.perf_counter() - t) * 1000, 1)

        sources = self._sources(chunks)
        trace = {
            "original_query": question,
            "standalone_query": standalone,
            "params": result["params"],
            "bm25": [slim(h) for h in result["bm25"]],
            "vector": [slim(h) for h in result["vector"]],
            "fused": [slim(h) for h in chunks],
            "prompt": prompt,
            "timings_ms": timings,
            "models": {"llm": s.gemini_llm_model, "embedding": s.gemini_embedding_model, "dims": s.embedding_dimensions},
        }

        self.pg.add_turn(session_id, question, answer, sources=sources, trace=trace)
        log.info("Answered session=%s in %.0f ms (top: %s)", session_id, sum(timings.values()), [c["chunk_id"] for c in chunks])
        return {"answer": answer, "sources": sources, "trace": trace}

    @staticmethod
    def _sources(chunks: List[dict]) -> List[dict]:
        return [
            {
                "n": i,  # the [n] the LLM cites
                "filename": c["filename"],
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "rrf_score": c["rrf_score"],
                "bm25_rank": c["contributions"].get("bm25", {}).get("rank"),
                "vector_rank": c["contributions"].get("vector", {}).get("rank"),
            }
            for i, c in enumerate(chunks, start=1)
        ]
