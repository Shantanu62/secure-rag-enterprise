
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PIIMatch:
    category: str
    start: int
    end: int
    value: str


PATTERNS = {
    "EMAIL": re.compile(
        r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(
        r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?"
        r"(?:\(?\d{3,5}\)?[\s.-]?)?"
        r"\d{3,5}[\s.-]?\d{4}(?!\w)"
    ),
    "SSN": re.compile(
        r"(?<!\d)(?!000|666|9\d{2})"
        r"\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?!\d)"
    ),
}


def detect_regex_pii(text: str) -> list[PIIMatch]:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    matches = []

    for category, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append(
                PIIMatch(
                    category=category,
                    start=match.start(),
                    end=match.end(),
                    value=match.group(),
                )
            )

    return sorted(matches, key=lambda item: (item.start, item.end))


def mask_regex_pii(text: str) -> str:
    matches = detect_regex_pii(text)

    for match in reversed(matches):
        replacement = f"[{match.category}]"
        text = (
            text[:match.start]
            + replacement
            + text[match.end:]
        )

    return text
