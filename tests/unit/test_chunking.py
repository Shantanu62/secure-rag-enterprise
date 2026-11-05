
import pytest

from backend.rag.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_returns_one_chunk():
    text = "Production RAG test document."

    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)

    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0


def test_long_text_is_split_into_multiple_chunks():
    text = "A" * 2500

    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=150)

    assert len(chunks) == 3
    assert [len(chunk.text) for chunk in chunks] == [1000, 1000, 800]


def test_chunk_overlap_is_preserved():
    text = "A" * 2500

    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=150)

    assert chunks[1].start_char == 850
    assert chunks[0].text[-150:] == chunks[1].text[:150]


def test_chunk_indexes_are_sequential():
    text = "A" * 2500

    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=150)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]


def test_invalid_chunk_size_raises_error():
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_text("Test", chunk_size=0)


def test_invalid_overlap_raises_error():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_text("Test", chunk_size=100, chunk_overlap=100)


def test_negative_overlap_raises_error():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_text("Test", chunk_size=100, chunk_overlap=-1)


def test_non_string_input_raises_error():
    with pytest.raises(TypeError, match="Input text"):
        chunk_text(None)
