import math

import pytest

from app.services.retrieval import tfidf_demo as t

CORPUS = {
    "d1": "apollo moon landing landing landing",
    "d2": "apollo thirteen oxygen tank",
    "d3": "mars rover helicopter",
    "d4": "mars rover mars mars",
}


def test_tokenize_lowercases_and_drops_stopwords():
    assert t.tokenize("The Moon IS in the sky") == ["moon", "sky"]


def test_idf_rare_terms_weigh_more():
    assert t.idf_classic(10, 1) > t.idf_classic(10, 9)
    assert t.idf_classic(10, 10) == 0.0  # appears everywhere -> carries no information


def test_bm25_idf_matches_lucene_formula_by_hand():
    # N=4 docs, term in n=1 doc  ->  ln(1 + (4 - 1 + 0.5) / (1 + 0.5))
    assert t.idf_bm25(4, 1) == pytest.approx(math.log(1 + 3.5 / 1.5))


def test_bm25_term_score_by_hand():
    # tf=2, dl=avgdl -> length factor = 1 ; tf_part = 2 / (2 + 1.2) = 0.625
    score = t.bm25_term_score(tf=2, df=1, n_docs=4, dl=10, avgdl=10, k1=1.2, b=0.75)
    assert score == pytest.approx(t.idf_bm25(4, 1) * 2 / (2 + 1.2))


def test_term_frequency_saturates():
    one = t.bm25_term_score(1, 1, 10, 10, 10)
    ten = t.bm25_term_score(10, 1, 10, 10, 10)
    hundred = t.bm25_term_score(100, 1, 10, 10, 10)
    assert one < ten < hundred
    assert ten < 10 * one  # 10x the occurrences is nowhere near 10x the score
    assert hundred < t.idf_bm25(10, 1) * 1.0  # upper bound = idf (tf_part < 1)


def test_longer_documents_score_lower_for_same_tf():
    short = t.bm25_term_score(2, 1, 10, dl=5, avgdl=10)
    long_ = t.bm25_term_score(2, 1, 10, dl=50, avgdl=10)
    assert short > long_


def test_b_zero_disables_length_normalization():
    a = t.bm25_term_score(2, 1, 10, dl=5, avgdl=10, b=0.0)
    b = t.bm25_term_score(2, 1, 10, dl=50, avgdl=10, b=0.0)
    assert a == pytest.approx(b)


def test_toy_index_ranks_the_right_document_first():
    idx = t.ToyIndex(CORPUS)
    bm25 = idx.bm25("oxygen apollo")
    assert max(bm25, key=bm25.get) == "d2"  # 'oxygen' is rare, so it decides
    tfidf = idx.tfidf("mars helicopter")
    assert max(tfidf, key=tfidf.get) == "d3"


def test_non_matching_doc_scores_zero():
    assert t.ToyIndex(CORPUS).bm25("moon")["d3"] == 0.0
