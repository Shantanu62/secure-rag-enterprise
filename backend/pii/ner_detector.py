
from functools import lru_cache

import spacy

from backend.pii.regex_detector import PIIMatch


MODEL_NAME = "en_core_web_sm"


@lru_cache(maxsize=1)
def get_nlp():
    try:
        return spacy.load(
            MODEL_NAME,
            disable=["tagger", "parser", "lemmatizer"],
        )
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{MODEL_NAME}' is not installed. "
            "Install it using: python -m spacy download en_core_web_sm"
        ) from exc


def detect_named_entities(text: str) -> list[PIIMatch]:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    if not text.strip():
        return []

    doc = get_nlp()(text)

    return [
        PIIMatch(
            category="PERSON",
            start=entity.start_char,
            end=entity.end_char,
            value=entity.text,
        )
        for entity in doc.ents
        if entity.label_ == "PERSON"
    ]
