import pytest

from app.services.retrieval.rrf import rrf_fuse


def test_worked_example_from_docstring():
    fused = rrf_fuse({"bm25": ["A", "B", "C"], "vector": ["C", "A", "D"]}, k=60)
    assert [f["id"] for f in fused] == ["A", "C", "B", "D"]
    scores = {f["id"]: f["score"] for f in fused}
    assert scores["A"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["C"] == pytest.approx(1 / 63 + 1 / 61)
    assert scores["B"] == pytest.approx(1 / 62)
    assert scores["D"] == pytest.approx(1 / 63)


def test_contributions_record_rank_per_list():
    fused = {f["id"]: f for f in rrf_fuse({"bm25": ["A", "B"], "vector": ["B"]})}
    assert fused["B"]["contributions"]["bm25"]["rank"] == 2
    assert fused["B"]["contributions"]["vector"]["rank"] == 1
    assert "vector" not in fused["A"]["contributions"]


def test_single_list_preserves_order():
    assert [f["id"] for f in rrf_fuse({"only": ["x", "y", "z"]})] == ["x", "y", "z"]


def test_agreement_beats_a_single_first_place():
    # D is #1 in one list only; A is #2 in both. Agreement should win.
    fused = rrf_fuse({"l1": ["D", "A"], "l2": ["X", "A"]}, k=60)
    assert fused[0]["id"] == "A"


def test_small_k_makes_top_rank_dominate():
    big_k = rrf_fuse({"l1": ["D", "A"], "l2": ["X", "A"]}, k=60)
    assert big_k[0]["id"] == "A"
    # with k=0 rank 1 is worth 1.0 and rank 2 only 0.5+0.5 = 1.0 -> tie, broken by id
    zero_k = rrf_fuse({"l1": ["D", "A"], "l2": ["X", "A"]}, k=0)
    assert zero_k[0]["score"] == pytest.approx(1.0)


def test_empty():
    assert rrf_fuse({}) == []
    assert rrf_fuse({"a": []}) == []
