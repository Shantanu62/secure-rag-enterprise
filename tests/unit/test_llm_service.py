from unittest.mock import MagicMock, patch

import pytest

from backend.rag.llm_service import (
    build_context,
    generate_answer,
)


@pytest.fixture
def retrieved_chunks():
    return [
        {
            "text": "Employees work from 9 AM to 6 PM.",
            "score": 0.92,
            "metadata": {
                "document_id": "1",
                "source_name": "employee_policy.txt",
            },
        },
        {
            "text": "The office remains closed on Sundays.",
            "score": 0.88,
            "metadata": {
                "document_id": "1",
                "source_name": "employee_policy.txt",
            },
        },
        {
            "text": "Annual leave allowance is 20 days.",
            "score": 0.85,
            "metadata": {
                "document_id": "2",
                "source_name": "leave_policy.txt",
            },
        },
    ]


def test_build_context_and_sources(retrieved_chunks):
    context, sources = build_context(retrieved_chunks)

    assert "Employees work from 9 AM to 6 PM." in context
    assert "Annual leave allowance is 20 days." in context

    assert "employee_policy.txt" not in context
    assert "leave_policy.txt" not in context

    assert len(sources) == 2
    assert sources[0]["filename"] == "employee_policy.txt"
    assert sources[1]["filename"] == "leave_policy.txt"


def test_build_context_empty_chunks():
    context, sources = build_context([])

    assert context == ""
    assert sources == []


def test_generate_answer_empty_chunks():
    result = generate_answer(
        question="What are the office hours?",
        retrieved_chunks=[],
    )

    assert "could not find relevant information" in result["answer"].lower()
    assert result["sources"] == []
    assert result["model"] is None


def test_generate_answer_empty_question(retrieved_chunks):
    with pytest.raises(ValueError, match="Question cannot be empty"):
        generate_answer("", retrieved_chunks)


def test_generate_answer_success(retrieved_chunks):
    mock_rails = MagicMock()

    mock_rails.generate.return_value = {
        "content": "Employees work from 9 AM to 6 PM. [Source 1]"
    }

    with patch(
        "backend.rag.llm_service.get_guardrails",
        return_value=mock_rails,
    ):
        result = generate_answer(
            question="What are the office hours?",
            retrieved_chunks=retrieved_chunks,
        )

    assert "9 AM to 6 PM" in result["answer"]
    assert len(result["sources"]) == 2
    assert result["model"] == "openai/gpt-oss-20b"

    mock_rails.generate.assert_called_once()

    call_args = mock_rails.generate.call_args
    messages = call_args.kwargs["messages"]

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "employee_policy.txt" not in messages[1]["content"]


def test_generate_answer_empty_response(retrieved_chunks):
    mock_rails = MagicMock()
    mock_rails.generate.return_value = {"content": ""}

    with (
        patch(
            "backend.rag.llm_service.get_guardrails",
            return_value=mock_rails,
        ),
        pytest.raises(RuntimeError, match="empty response"),
    ):
        generate_answer(
            question="What are the office hours?",
            retrieved_chunks=retrieved_chunks,
        )


def test_generate_answer_invalid_chunks():
    with pytest.raises(ValueError, match="Retrieved chunks must be a list"):
        generate_answer(
            question="What are the office hours?",
            retrieved_chunks=None,
        )
