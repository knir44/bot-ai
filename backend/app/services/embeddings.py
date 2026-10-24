"""Embeddings via the Gemini API.

WHAT IS AN EMBEDDING?
  A neural network reads a text and outputs a list of numbers (here 768) - a point in a
  768-dimensional space. Texts with similar MEANING land close together, even with zero
  shared words: "red planet robot" lands near "Mars rover". That is what BM25 cannot do.

COSINE SIMILARITY
  cos(a, b) = (a . b) / (|a| |b|)  ->  1 = same direction (same meaning), 0 = unrelated.
  If every vector is scaled to length 1 (L2-normalized), cosine is just the dot product,
  which is what vector databases compute fastest. That is why we normalize below.

TASK TYPES (asymmetric search)
  A question ("who first walked on the Moon?") and its answer passage look nothing alike.
  The model was trained with two modes so they still land near each other:
     RETRIEVAL_DOCUMENT  for chunks we store,   RETRIEVAL_QUERY  for the user's question.
  Using the wrong one silently degrades quality.

DIMENSIONS
  gemini-embedding-001 outputs 3072 numbers natively but is trained so that the FIRST n
  numbers are still a good embedding (Matryoshka). We truncate to 768: 4x less storage and
  faster search. Truncated vectors are no longer unit length, hence the re-normalization.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import List, Tuple

import numpy as np

from app.config import get_settings

log = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_RETRIES = 5


class EmbeddingError(RuntimeError):
    pass


@lru_cache
def _client():
    from google import genai

    key = get_settings().gemini_api_key
    if not key:
        raise EmbeddingError("GEMINI_API_KEY לא הוגדר. מוסיפים אותו לקובץ .env ומפעילים מחדש את הבקאנד.")
    return genai.Client(api_key=key)


def _normalize(vec: List[float]) -> List[float]:
    arr = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist() if norm > 0 else arr.tolist()


def _embed_batch(texts: List[str], task_type: str) -> List[List[float]]:
    from google.genai import types

    s = get_settings()
    for attempt in range(MAX_RETRIES):
        try:
            resp = _client().models.embed_content(
                model=s.gemini_embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=s.embedding_dimensions),
            )
            return [_normalize(e.values) for e in resp.embeddings]
        except EmbeddingError:
            raise
        except Exception as exc:  # rate limit (429), transient 5xx...
            wait = 2**attempt
            log.warning("Embedding batch failed (%s); retry %d/%d in %ds", exc, attempt + 1, MAX_RETRIES, wait)
            if attempt == MAX_RETRIES - 1:
                raise EmbeddingError(f"הבקשה ל-Gemini ליצירת embeddings נכשלה: {exc}") from exc
            time.sleep(wait)
    raise EmbeddingError("unreachable")


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed chunks for storage (RETRIEVAL_DOCUMENT), in batches."""
    out: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        out.extend(_embed_batch(texts[i : i + BATCH_SIZE], "RETRIEVAL_DOCUMENT"))
    return out


@lru_cache(maxsize=256)
def _embed_query_cached(text: str) -> Tuple[float, ...]:
    return tuple(_embed_batch([text], "RETRIEVAL_QUERY")[0])


def embed_query(text: str) -> List[float]:
    """Embed a question (RETRIEVAL_QUERY). Cached: the Lab re-runs the same query often."""
    return list(_embed_query_cached(text))
