from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_es
from app.api.v1 import chat, documents, health, lab
from app.config import get_settings
from app.core.logging_config import setup_logging
from app.repositories import pg_repo
from app.services.ingestion import ingest_sample_corpus

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    setup_logging(s.log_dir)
    log.info("Starting DocuMind RAG (llm=%s, embeddings=%s/%dd)", s.gemini_llm_model, s.gemini_embedding_model, s.embedding_dimensions)
    if s.session_secret == "dev-secret-change-me":
        log.warning("SESSION_SECRET is the default value - set a real one in .env")
    if not s.gemini_api_key:
        log.warning("GEMINI_API_KEY is empty: search works only after you set it (embeddings + answers need Gemini)")
    pg_repo.init_db()
    es = get_es()
    es.ensure_index()
    if s.auto_seed_sample and s.gemini_api_key and es.count() == 0:
        # In a background thread so the API is up immediately; embedding ~40 chunks takes a few seconds.
        threading.Thread(target=_seed_sample, args=(es,), daemon=True).start()
    yield


def _seed_sample(es) -> None:
    try:
        results = ingest_sample_corpus(es)
        log.info("Auto-loaded sample corpus: %d documents, %d chunks", len(results), sum(r["chunks"] for r in results))
    except Exception:
        log.exception("Auto-loading the sample corpus failed (you can still load it from the UI or upload your own files)")


app = FastAPI(title="DocuMind RAG", version="1.0.0", lifespan=lifespan)

# CORS: only the listed browser origins may call the API from JavaScript.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Session-Id", "X-Session-Token"],
)

for r in (health.router, documents.router, chat.router, lab.router):
    app.include_router(r, prefix="/api/v1")
