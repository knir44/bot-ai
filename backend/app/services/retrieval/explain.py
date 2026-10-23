"""Turn Elasticsearch's `explain=true` tree into a flat, human-readable BM25 breakdown.

ES returns a deeply nested tree such as:

    weight(content:mar in 3)  ->  score(freq=2.0), computed as boost * idf * tf from:
        idf, computed as log(1 + (N - n + 0.5) / (n + 0.5))   [n = docs containing term, N = total docs]
        tf,  computed as freq / (freq + k1 * (1 - b + b * dl / avgdl))

We extract the numbers so the UI can show the very formula from tfidf_demo.py filled in with real values.
Note the term is the *stemmed* token ("mars" -> "mar"), which is why stemming matters when debugging BM25.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional

_TERM_RE = re.compile(r"weight\([^:]+:(.+?) in \d+\)")


def _find(node: dict, prefix: str) -> Optional[dict]:
    if node.get("description", "").startswith(prefix):
        return node
    for child in node.get("details", []):
        found = _find(child, prefix)
        if found:
            return found
    return None


def _value(node: dict, prefix: str) -> Optional[float]:
    found = _find(node, prefix)
    return found["value"] if found else None


def _weights(node: dict) -> List[dict]:
    if node.get("description", "").startswith("weight("):
        return [node]
    out: List[dict] = []
    for child in node.get("details", []):
        out.extend(_weights(child))
    return out


def parse_bm25_explanation(explanation: Optional[dict]) -> List[dict[str, Any]]:
    """One entry per matched query term, with every ingredient of its BM25 score."""
    if not explanation:
        return []
    terms = []
    for w in _weights(explanation):
        m = _TERM_RE.match(w["description"])
        terms.append(
            {
                "term": m.group(1) if m else "?",
                "score": w["value"],
                "idf": _value(w, "idf"),
                "tf_norm": _value(w, "tf"),  # the saturated, length-normalised tf in (0, 1)
                "freq": _value(w, "freq"),  # raw count of the term in this chunk
                "docs_with_term": _value(w, "n,"),
                "total_docs": _value(w, "N,"),
                "field_length": _value(w, "dl,"),
                "avg_field_length": _value(w, "avgdl,"),
                "k1": _value(w, "k1"),
                "b": _value(w, "b,"),
            }
        )
    return terms
