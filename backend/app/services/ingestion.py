"""Ingestion pipeline:  validate -> parse -> chunk -> embed -> index.

Shared by the upload endpoint and the sample-corpus seeder so both behave identically.
"""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import List

from app.config import get_settings
from app.core.security import ValidationError, validate_upload
from app.repositories.es_repo import EsRepository
from app.services import embeddings
from app.services.chunking import chunk_text
from app.services.parsing import extract_text

log = logging.getLogger(__name__)


def ingest_bytes(filename: str, data: bytes, es: EsRepository) -> dict:
    s = get_settings()
    safe_name, ext = validate_upload(filename, data, s.max_upload_mb * 1024 * 1024)

    t0 = time.perf_counter()
    text = extract_text(data, ext)
    chunks = chunk_text(text, s.chunk_size, s.chunk_overlap)
    if not chunks:
        raise ValidationError("No extractable text found (scanned PDFs need OCR, which is not supported).")

    # doc_id = hash of the content: uploading the identical file again replaces it instead of duplicating it.
    doc_id = hashlib.sha256(data).hexdigest()[:16]
    vectors = embeddings.embed_documents(chunks)
    es.index_chunks(doc_id, safe_name, chunks, vectors)

    elapsed = round((time.perf_counter() - t0) * 1000)
    log.info("Ingested %s: %d chars -> %d chunks in %d ms", safe_name, len(text), len(chunks), elapsed)
    return {"doc_id": doc_id, "filename": safe_name, "characters": len(text), "chunks": len(chunks), "elapsed_ms": elapsed}


def ingest_sample_corpus(es: EsRepository) -> List[dict]:
    folder = Path(get_settings().sample_corpus_dir)
    results = []
    for path in sorted(folder.glob("*.txt")):
        results.append(ingest_bytes(path.name, path.read_bytes(), es))
    return results
