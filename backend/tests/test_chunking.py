import pytest

from app.services.chunking import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.", size=800, overlap=100) == ["Hello world."]


def test_no_chunk_exceeds_size():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 80 for i in range(20))
    chunks = chunk_text(text, size=300, overlap=50)
    assert len(chunks) > 5
    assert all(len(c) <= 300 for c in chunks)


def test_overlap_repeats_text_between_neighbours():
    sentences = [f"Sentence number {i} talks about topic {i}." for i in range(60)]
    chunks = chunk_text(" ".join(sentences), size=200, overlap=60)
    assert len(chunks) > 3
    for prev, nxt in zip(chunks, chunks[1:]):
        # the beginning of the next chunk must already appear at the end of the previous one
        first_words = " ".join(nxt.split()[:3])
        assert first_words in prev


def test_no_overlap_when_zero():
    text = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_text(text, size=100, overlap=0)
    assert " ".join(chunks).split() == text.split()  # nothing lost, nothing duplicated


def test_nothing_is_lost_without_overlap_on_paragraphs():
    paras = [f"Paragraph {i} " + "x" * 150 for i in range(10)]
    chunks = chunk_text("\n\n".join(paras), size=400, overlap=0)
    joined = "\n\n".join(chunks)
    for p in paras:
        assert p in joined


def test_giant_word_is_hard_cut():
    chunks = chunk_text("a" * 1000, size=300, overlap=0)
    assert [len(c) for c in chunks] == [300, 300, 300, 100]


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("abc", size=100, overlap=100)


def test_empty_text():
    assert chunk_text("   \n\n  ") == []
