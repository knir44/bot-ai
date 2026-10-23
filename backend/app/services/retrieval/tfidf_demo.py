"""TF-IDF and BM25 from scratch - for learning, not for production (Elasticsearch does the real work).

Run it:   python -m app.services.retrieval.tfidf_demo

TF-IDF  = "how often does the word appear HERE" x "how rare is the word EVERYWHERE"
  tf(t, d)  = count of t in d
  idf(t)    = log(N / df(t))             N = number of docs, df = docs containing t
  A word like "the" appears in every doc -> idf = log(1) = 0 -> worthless.
  A word like "Perseverance" appears in one doc -> huge idf -> very informative.

BM25 is TF-IDF with two fixes (this is what Elasticsearch/Lucene use by default):
  1. TERM-FREQUENCY SATURATION. Seeing a word 20 times is not 20x more relevant than once.
        tf_part = tf / (tf + k1 * (...))        -> climbs fast, then flattens (limit = 1)
     k1 (default 1.2) controls how quickly it saturates.
  2. LENGTH NORMALIZATION. A word in a 20-word chunk matters more than in a 2000-word one.
        (...) = 1 - b + b * (dl / avgdl)         dl = this doc's length, avgdl = average length
     b (default 0.75) controls how much length matters (0 = ignore length, 1 = full).

  BM25(q, d) = sum over query terms t of   idf(t) * tf / (tf + k1 * (1 - b + b * dl/avgdl))
  with Lucene's idf:   idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5))   (always positive)
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "a", "an", "of", "and", "to", "in", "is", "it", "was", "on", "for", "with", "as", "by", "at"}


def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumerics, drop stop words. (ES also stems: 'landing' -> 'land'.)"""
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def idf_classic(n_docs: int, df: int) -> float:
    return math.log(n_docs / df) if df else 0.0


def idf_bm25(n_docs: int, df: int) -> float:
    """Lucene/Elasticsearch IDF. The +1 inside the log keeps it positive even for very common terms."""
    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))


def bm25_term_score(tf: float, df: int, n_docs: int, dl: float, avgdl: float, k1: float = 1.2, b: float = 0.75) -> float:
    """BM25 contribution of ONE query term to ONE document. Same formula as ES `explain` shows."""
    if tf == 0:
        return 0.0
    tf_part = tf / (tf + k1 * (1 - b + b * dl / avgdl))
    return idf_bm25(n_docs, df) * tf_part


class ToyIndex:
    """A tiny in-memory index so you can see every number."""

    def __init__(self, docs: Dict[str, str]):
        self.tokens = {doc_id: tokenize(text) for doc_id, text in docs.items()}
        self.tf = {doc_id: Counter(toks) for doc_id, toks in self.tokens.items()}
        self.n_docs = len(docs)
        self.df: Counter = Counter()
        for counts in self.tf.values():
            self.df.update(counts.keys())
        self.avgdl = sum(len(t) for t in self.tokens.values()) / max(self.n_docs, 1)

    def tfidf(self, query: str) -> Dict[str, float]:
        scores = {}
        for doc_id, counts in self.tf.items():
            dl = len(self.tokens[doc_id])
            # length-normalized tf (a common TF-IDF variant): count / doc length
            scores[doc_id] = sum((counts[t] / dl) * idf_classic(self.n_docs, self.df[t]) for t in tokenize(query) if counts[t])
        return scores

    def bm25(self, query: str, k1: float = 1.2, b: float = 0.75) -> Dict[str, float]:
        scores = {}
        for doc_id, counts in self.tf.items():
            dl = len(self.tokens[doc_id])
            scores[doc_id] = sum(
                bm25_term_score(counts[t], self.df[t], self.n_docs, dl, self.avgdl, k1, b)
                for t in tokenize(query)
                if counts[t]
            )
        return scores


if __name__ == "__main__":
    corpus = {
        "apollo11": "Apollo 11 landed on the Moon in 1969. Neil Armstrong walked on the Moon.",
        "apollo13": "Apollo 13 suffered an oxygen tank explosion on the way to the Moon. The crew returned safely.",
        "perseverance": "Perseverance rover landed on Mars in 2021 carrying the Ingenuity helicopter.",
    }
    index = ToyIndex(corpus)
    query = "Moon landing Apollo 13"
    print(f"query: {query!r}   tokens: {tokenize(query)}\n")
    print(f"{'doc':<14}{'TF-IDF':>10}{'BM25':>10}")
    tfidf, bm25 = index.tfidf(query), index.bm25(query)
    for doc_id in sorted(corpus, key=lambda d: -bm25[d]):
        print(f"{doc_id:<14}{tfidf[doc_id]:>10.4f}{bm25[doc_id]:>10.4f}")
    print("\nNotice: 'apollo' and 'moon' appear in several docs (low idf); '13' only in apollo13 (high idf).")
