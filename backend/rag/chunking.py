
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    start_char: int
    end_char: int


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[TextChunk]:
    """
    Split text into overlapping character-based chunks.

    Args:
        text: Input document text.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Characters shared between consecutive chunks.
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    if not text.strip():
        return []

    chunks = []
    start = 0
    index = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_content = text[start:end]

        if chunk_content.strip():
            chunks.append(
                TextChunk(
                    chunk_index=index,
                    text=chunk_content,
                    start_char=start,
                    end_char=end,
                )
            )
            index += 1

        if end == text_length:
            break

        start = end - chunk_overlap

    return chunks
