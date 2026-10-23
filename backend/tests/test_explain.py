from app.services.retrieval.explain import parse_bm25_explanation

# Shape of a real `explain=true` response from Elasticsearch 8.x for a one-term match query.
EXPLANATION = {
    "value": 2.5,
    "description": "weight(content:mar in 3) [PerFieldSimilarity], result of:",
    "details": [
        {
            "value": 2.5,
            "description": "score(freq=3.0), computed as boost * idf * tf from:",
            "details": [
                {"value": 2.2, "description": "boost", "details": []},
                {
                    "value": 1.9,
                    "description": "idf, computed as log(1 + (N - n + 0.5) / (n + 0.5)) from:",
                    "details": [
                        {"value": 4, "description": "n, number of documents containing term", "details": []},
                        {"value": 38, "description": "N, total number of documents with field", "details": []},
                    ],
                },
                {
                    "value": 0.6,
                    "description": "tf, computed as freq / (freq + k1 * (1 - b + b * dl / avgdl)) from:",
                    "details": [
                        {"value": 3.0, "description": "freq, occurrences of term within document", "details": []},
                        {"value": 1.2, "description": "k1, term saturation parameter", "details": []},
                        {"value": 0.75, "description": "b, length normalization parameter", "details": []},
                        {"value": 70.0, "description": "dl, length of field (approximate)", "details": []},
                        {"value": 80.0, "description": "avgdl, average length of field", "details": []},
                    ],
                },
            ],
        }
    ],
}


def test_parses_one_term():
    (term,) = parse_bm25_explanation(EXPLANATION)
    assert term["term"] == "mar"
    assert term["freq"] == 3.0
    assert term["docs_with_term"] == 4 and term["total_docs"] == 38
    assert term["idf"] == 1.9 and term["tf_norm"] == 0.6
    assert term["k1"] == 1.2 and term["b"] == 0.75
    assert term["field_length"] == 70.0 and term["avg_field_length"] == 80.0


def test_multiple_terms_under_a_sum_node():
    root = {"value": 5.0, "description": "sum of:", "details": [EXPLANATION, EXPLANATION]}
    assert len(parse_bm25_explanation(root)) == 2


def test_none():
    assert parse_bm25_explanation(None) == []
