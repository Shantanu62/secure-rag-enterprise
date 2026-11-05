
from backend.rag.embeddings import embed_documents, embed_query
from backend.rag.vector_store import (
    index_chunks,
    search_chunks,
    delete_document_chunks,
)


def test_embedding_and_qdrant_retrieval():
    document_id = "embedding-test-document"
    organization_id = "embedding-test-organization"

    chunks = [
        "The company provides secure document processing.",
        "Role based access control protects confidential documents.",
    ]

    metadata = {
        "organization_id": organization_id,
        "document_id": document_id,
        "department": "Engineering",
        "allowed_roles": ["Admin", "Manager"],
        "source_name": "synthetic-test.txt",
    }

    try:
        embeddings = embed_documents(chunks)

        assert len(embeddings) == 2
        assert all(len(vector) == 384 for vector in embeddings)

        query_vector = embed_query(
            "How does the company protect documents?"
        )

        assert len(query_vector) == 384

        indexed_count = index_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
        )

        assert indexed_count == 2

        results = search_chunks(
            query_embedding=query_vector,
            organization_id=organization_id,
            department="Engineering",
            role="Manager",
        )

        assert len(results) > 0
        assert all(
            result["metadata"]["organization_id"] == organization_id
            for result in results
        )

        assert any(
            "document" in result["text"].lower()
            for result in results
        )

    finally:
        delete_document_chunks(document_id)
