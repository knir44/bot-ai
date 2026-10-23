"""Recursive chunking.

WHY CHUNK AT ALL?
  An embedding turns a whole text into ONE vector. A 20-page PDF squeezed into one vector is
  a blurry average of everything. Small, focused chunks give sharp vectors, and the LLM only
  receives the few chunks that matter instead of the whole document.

WHY "RECURSIVE"?
  We try to cut at the most natural boundary first: paragraph break -> line break -> sentence
  end -> space -> (last resort) raw characters. A chunk that ends mid-sentence hurts both
  BM25 and embeddings.

WHY OVERLAP?
  A fact that straddles a cut ("...landed on the Moon. | It happened on July 20...") would be
  split in two. Repeating the last ~100 characters of a chunk at the start of the next one
  keeps such facts together in at least one chunk.
"""
from __future__ import annotations

import re
from typing import List

SEPARATORS = ["\n\n", "\n", ". ", " "]


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split(text: str, size: int, seps: List[str]) -> List[str]:
    """Break `text` into pieces no longer than `size`, preferring the earliest separator."""
    if len(text) <= size:
        return [text]
    if not seps:  # nothing natural left to cut on: hard cut
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    if sep not in text:
        return _split(text, size, rest)
    parts = text.split(sep)
    pieces: List[str] = []
    for i, part in enumerate(parts):
        piece = part + (sep if i < len(parts) - 1 else "")  # keep the separator so nothing is lost
        pieces.extend(_split(piece, size, rest) if len(piece) > size else [piece])
    return pieces


def _overlap_tail(chunk: str, overlap: int) -> str:
    """Last `overlap` chars of a chunk, moved forward to start on a word boundary."""
    if overlap <= 0 or len(chunk) <= overlap:
        return ""
    tail = chunk[-overlap:]
    space = tail.find(" ")
    return tail[space + 1 :] if space != -1 else tail


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into chunks of at most `size` characters with ~`overlap` characters of overlap."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    pieces = _split(_normalize(text), size, SEPARATORS)

    chunks: List[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current.strip())
            tail = _overlap_tail(current, overlap)
            current = tail + piece if len(tail) + len(piece) <= size else piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]
