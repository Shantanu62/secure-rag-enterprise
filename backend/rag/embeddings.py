
from functools import lru_cache
from collections.abc import Sequence

from fastembed import TextEmbedding

from backend.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """Load and cache the configured embedding model."""
    return TextEmbedding(
        model_name=settings.EMBEDDING_MODEL,
    )


def embed_documents(texts: Sequence[str]) -> list[list[float]]:
    """Convert document chunks into dense embedding vectors."""
    if not texts:
        return []

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("All document texts must be non-empty strings")

    model = get_embedding_model()
    vectors = list(model.embed(list(texts)))

    results = []

    for vector in vectors:
        values = vector.tolist()

        if len(values) != settings.EMBEDDING_DIMENSION:
            raise ValueError("Embedding dimension mismatch")

        results.append(values)

    return results


def embed_query(query: str) -> list[float]:
    """Convert a search query into a dense embedding vector."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string")

    model = get_embedding_model()
    vector = next(model.query_embed(query))
    values = vector.tolist()

    if len(values) != settings.EMBEDDING_DIMENSION:
        raise ValueError("Embedding dimension mismatch")

    return values
