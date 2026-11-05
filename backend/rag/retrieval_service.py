
from pathlib import Path

from backend.core.config import settings
from backend.rag.chunking import chunk_text
from backend.rag.document_loader import load_document
from backend.rag.embeddings import embed_documents, embed_query
from backend.rag.vector_store import (
    index_chunks,
    search_chunks,
    delete_document_chunks,
)


def index_document(file_path: str | Path, metadata: dict) -> int:
    """Load, chunk, embed, and index a document."""
    text = load_document(file_path)

    chunks = chunk_text(
        text,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    if not chunks:
        return 0

    chunk_texts = [chunk.text for chunk in chunks]
    embeddings = embed_documents(chunk_texts)

    return index_chunks(
        chunks=chunk_texts,
        embeddings=embeddings,
        metadata=metadata,
    )


def retrieve_documents(
    query: str,
    department: str,
    role: str,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve document chunks authorized for the user."""
    query_embedding = embed_query(query)

    return search_chunks(
        query_embedding=query_embedding,
        department=department,
        role=role,
        limit=limit,
    )


def remove_document_from_index(document_id: str) -> None:
    """Remove all indexed chunks for a document."""
    delete_document_chunks(document_id)
