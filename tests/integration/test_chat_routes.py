
import pytest

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth.dependencies import get_current_user


@pytest.fixture
def chat_environment():
    current_user = {
        "user_id": "1",
        "username": "chat_admin",
        "role": "Admin",
        "department": "Engineering",
    }

    app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app)

    yield {
        "client": client,
        "current_user": current_user,
    }

    client.close()
    app.dependency_overrides.clear()


def test_authenticated_user_can_ask_question(chat_environment):
    from unittest.mock import patch

    with patch(
        "backend.api.chat_routes.answer_question",
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
            "pii_masking_enabled": True,
        },
    ) as mock_answer:
        response = chat_environment["client"].post(
            "/chat/ask",
            json={"question": "What are the office hours?"},
        )

    assert response.status_code == 200

    data = response.json()

    assert "9 AM to 6 PM" in data["answer"]
    assert data["sources"][0]["filename"] == "employee_policy.txt"
    assert data["pii_masking_enabled"] is True

    mock_answer.assert_called_once_with(
        question="What are the office hours?",
        department="Engineering",
        role="Admin",
    )


def test_employee_can_ask_question(chat_environment):
    from unittest.mock import patch

    chat_environment["current_user"].update({
        "role": "Employee",
        "department": "HR",
    })

    with patch(
        "backend.api.chat_routes.answer_question",
        return_value={
            "answer": "Answer found.",
            "sources": [],
            "model": "test-model",
            "pii_masking_enabled": True,
        },
    ) as mock_answer:
        response = chat_environment["client"].post(
            "/chat/ask",
            json={"question": "What is the leave policy?"},
        )

    assert response.status_code == 200

    mock_answer.assert_called_once_with(
        question="What is the leave policy?",
        department="HR",
        role="Employee",
    )


def test_user_without_permission_cannot_ask(chat_environment):
    chat_environment["current_user"]["role"] = "Guest"

    response = chat_environment["client"].post(
        "/chat/ask",
        json={"question": "Show me confidential documents"},
    )

    assert response.status_code == 403


def test_chat_rejects_empty_question(chat_environment):
    response = chat_environment["client"].post(
        "/chat/ask",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_chat_handles_answer_validation_error(chat_environment):
    from unittest.mock import patch

    with patch(
        "backend.api.chat_routes.answer_question",
        side_effect=ValueError("Invalid question"),
    ):
        response = chat_environment["client"].post(
            "/chat/ask",
            json={"question": "Test question"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid question"


def test_chat_handles_llm_failure(chat_environment):
    from unittest.mock import patch

    with patch(
        "backend.api.chat_routes.answer_question",
        side_effect=RuntimeError("Provider failure"),
    ):
        response = chat_environment["client"].post(
            "/chat/ask",
            json={"question": "Test question"},
        )

    assert response.status_code == 502
    assert "Unable to generate an answer" in response.json()["detail"]
