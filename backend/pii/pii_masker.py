
from backend.pii.regex_detector import (
    PIIMatch,
    detect_regex_pii,
)
from backend.pii.ner_detector import detect_named_entities


def detect_pii(text: str) -> list[PIIMatch]:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    if not text.strip():
        return []

    matches = (
        detect_regex_pii(text)
        + detect_named_entities(text)
    )

    # Prefer longer matches when detected spans overlap.
    matches.sort(
        key=lambda item: (
            item.start,
            -(item.end - item.start),
        )
    )

    filtered = []

    for match in matches:
        if filtered and match.start < filtered[-1].end:
            continue

        filtered.append(match)

    return filtered


def mask_pii(text: str) -> str:
    matches = detect_pii(text)

    for match in reversed(matches):
        replacement = f"[{match.category}]"
        text = (
            text[:match.start]
            + replacement
            + text[match.end:]
        )

    return text
