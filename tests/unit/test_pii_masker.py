
import pytest

from backend.pii.pii_masker import detect_pii, mask_pii


def test_detect_email():
    matches = detect_pii("Contact us at john@example.com")
    assert any(match.category == "EMAIL" for match in matches)


def test_detect_indian_phone():
    matches = detect_pii("Call +91 9876543210")
    assert any(match.category == "PHONE" for match in matches)


def test_detect_us_ssn():
    matches = detect_pii("SSN: 123-45-6789")
    assert any(match.category == "SSN" for match in matches)


def test_detect_person_name():
    matches = detect_pii("John Doe works here")
    assert any(
        match.category == "PERSON" and match.value == "John Doe"
        for match in matches
    )


def test_mask_all_pii_categories():
    text = (
        "John Doe, john@example.com, "
        "+91 9876543210, SSN 123-45-6789"
    )

    masked = mask_pii(text)

    assert "[PERSON]" in masked
    assert "[EMAIL]" in masked
    assert "[PHONE]" in masked
    assert "[SSN]" in masked

    assert "John Doe" not in masked
    assert "john@example.com" not in masked
    assert "9876543210" not in masked
    assert "123-45-6789" not in masked


def test_empty_text():
    assert detect_pii("") == []
    assert mask_pii("") == ""


def test_invalid_input():
    with pytest.raises(TypeError):
        detect_pii(None)

    with pytest.raises(TypeError):
        mask_pii(None)


def test_normal_text_without_pii():
    text = "The project meeting is scheduled for Monday."
    assert mask_pii(text) == text
