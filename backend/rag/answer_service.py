
from backend.core.config import settings
from backend.pii.pii_masker import mask_pii
from backend.rag.llm_service import generate_answer
from backend.rag.retrieval_service import retrieve_documents


def answer_question(
    question: str,
    department: str,
    role: str,
    limit: int | None = None,
) -> dict:
    """Retrieve authorized documents, mask PII, and generate an answer."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty")

    if not isinstance(department, str) or not department.strip():
        raise ValueError("Department cannot be empty")

    if not isinstance(role, str) or not role.strip():
        raise ValueError("Role cannot be empty")

    # Retrieve only documents accessible to this user's role and department.
    retrieved_chunks = retrieve_documents(
        query=question,
        department=department,
        role=role,
        limit=limit,
    )

    if not retrieved_chunks:
        return {
            "answer": (
                "I could not find relevant information in your "
                "accessible documents."
            ),
            "sources": [],
            "model": None,
            "pii_masking_enabled": settings.PII_MASKING_ENABLED,
        }

    # Never send unmasked question or document content to the LLM.
    safe_question = question
    safe_chunks = retrieved_chunks

    if settings.PII_MASKING_ENABLED:
        safe_question = mask_pii(question)

        safe_chunks = []

        for chunk in retrieved_chunks:
            safe_chunk = dict(chunk)
            safe_chunk["text"] = mask_pii(chunk.get("text", ""))

            metadata = dict(chunk.get("metadata", {}))

            # Keep original source metadata for citation mapping.
            safe_chunk["metadata"] = metadata
            safe_chunks.append(safe_chunk)

    result = generate_answer(
        question=safe_question,
        retrieved_chunks=safe_chunks,
    )

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "model": result["model"],
        "pii_masking_enabled": settings.PII_MASKING_ENABLED,
    }
