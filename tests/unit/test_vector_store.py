from backend.rag.embeddings import embed_documents, embed_query
from backend.rag.vector_store import (
    index_chunks,
    search_chunks,
    delete_document_chunks,
)
def test_embedding_and_qdrant_retrieval():
    document_id = "embedding-test-document"
    chunks = [
        "The company provides secure document processing.",
        "Role based access control protects confidential documents.",
    ]
    metadata = {
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
        manager_results = search_chunks(
            query_embedding=query_vector,
            department="Engineering",
            role="Manager",
        )
        assert any(
            result["metadata"]["document_id"] == document_id
            for result in manager_results
        )
        assert any(
            "document" in result["text"].lower()
            for result in manager_results
            if result["metadata"]["document_id"] == document_id
        )
        employee_results = search_chunks(
            query_embedding=query_vector,
            department="Engineering",
            role="Employee",
        )
        assert not any(
            result["metadata"]["document_id"] == document_id
            for result in employee_results
        )
        other_department_results = search_chunks(
            query_embedding=query_vector,
            department="Finance",
            role="Manager",
        )
        assert not any(
            result["metadata"]["document_id"] == document_id
            for result in other_department_results
        )
    finally:
        delete_document_chunks(document_id)
