
from unittest.mock import patch

import pytest

from backend.rag.answer_service import answer_question


@pytest.fixture
def retrieved_chunks():
    return [
        {
            "text": (
                "Contact John Smith at john@example.com. "
                "Office hours are 9 AM to 6 PM."
            ),
            "score": 0.95,
            "metadata": {
                "document_id": "101",
                "source_name": "employee_policy.txt",
                "department": "HR",
                "allowed_roles": ["Admin", "Employee"],
            },
        }
    ]


def test_answer_question_masks_pii_before_llm(retrieved_chunks):
    with (
        patch(
            "backend.rag.answer_service.retrieve_documents",
            return_value=retrieved_chunks,
        ) as mock_retrieve,
        patch(
            "backend.rag.answer_service.mask_pii",
            side_effect=lambda text: (
                text.replace("john@example.com", "[EMAIL]")
                .replace("John Smith", "[PERSON]")
            ),
        ),
        patch(
            "backend.rag.answer_service.settings.PII_MASKING_ENABLED",
            True,
        ),
        patch(
            "backend.rag.answer_service.generate_answer",
            return_value={
                "answer": "Office hours are 9 AM to 6 PM. [Source 1]",
                "sources": [
                    {
                        "source_number": 1,
                        "document_id": "101",
                        "filename": "employee_policy.txt",
                    }
                ],
                "model": "test-model",
            },
        ) as mock_generate,
    ):
        result = answer_question(
            question="Contact John Smith at john@example.com",
            department="HR",
            role="Employee",
        )

    mock_retrieve.assert_called_once()

    sent_question = mock_generate.call_args.kwargs["question"]
    sent_chunks = mock_generate.call_args.kwargs["retrieved_chunks"]

    assert "john@example.com" not in sent_question
    assert "John Smith" not in sent_question
    assert "[EMAIL]" in sent_question
    assert "[PERSON]" in sent_question

    assert "john@example.com" not in sent_chunks[0]["text"]
    assert "John Smith" not in sent_chunks[0]["text"]

    assert (
        sent_chunks[0]["metadata"]["source_name"]
        == "employee_policy.txt"
    )

    assert result["pii_masking_enabled"] is True
    assert result["sources"][0]["filename"] == "employee_policy.txt"


def test_answer_question_without_pii_masking(retrieved_chunks):
    with (
        patch(
            "backend.rag.answer_service.retrieve_documents",
            return_value=retrieved_chunks,
        ),
        patch(
            "backend.rag.answer_service.settings.PII_MASKING_ENABLED",
            False,
        ),
        patch(
            "backend.rag.answer_service.generate_answer",
            return_value={
                "answer": "Office hours are 9 AM to 6 PM.",
                "sources": [],
                "model": "test-model",
            },
        ) as mock_generate,
    ):
        result = answer_question(
            question="Contact John Smith",
            department="HR",
            role="Employee",
        )

    sent_question = mock_generate.call_args.kwargs["question"]
    sent_chunks = mock_generate.call_args.kwargs["retrieved_chunks"]

    assert sent_question == "Contact John Smith"
    assert "john@example.com" in sent_chunks[0]["text"]
    assert result["pii_masking_enabled"] is False


def test_answer_question_without_retrieved_documents():
    with (
        patch(
            "backend.rag.answer_service.retrieve_documents",
            return_value=[],
        ),
        patch(
            "backend.rag.answer_service.generate_answer",
        ) as mock_generate,
    ):
        result = answer_question(
            question="What are the office hours?",
            department="HR",
            role="Employee",
        )

    assert result["sources"] == []
    assert result["model"] is None
    mock_generate.assert_not_called()


@pytest.mark.parametrize(
    "question,department,role",
    [
        ("", "HR", "Employee"),
        ("Question", "", "Employee"),
        ("Question", "HR", ""),
    ],
)
def test_answer_question_rejects_empty_inputs(
    question,
    department,
    role,
):
    with pytest.raises(ValueError):
        answer_question(
            question=question,
            department=department,
            role=role,
        )
