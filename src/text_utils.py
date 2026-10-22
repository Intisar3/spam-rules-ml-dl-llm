"""Shared text helpers for Arabic + English messages."""
import re

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
AR_DIACRITICS = re.compile(r"[ً-ْـ]")  # tashkeel + tatweel


def normalize_same_length(text: str) -> str:
    """Lowercase and unify Arabic letter variants, one char in, one char out.

    Keeping the length the same means a match found in the normalized text
    points to the exact same position in the original text, which is what
    the highlighter needs.
    """
    text = text.lower()
    text = re.sub("[أإآ]", "ا", text)
    return text.replace("ى", "ي").replace("ة", "ه")


def normalize(text: str) -> str:
    """Full normalization for models (also strips diacritics)."""
    return AR_DIACRITICS.sub("", normalize_same_length(text))


def word_spans(text: str):
    """Return (start, end, word) for every word in the original text."""
    return [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(text)]


def analyzer(text: str):
    """Tokenizer used by TF-IDF: normalized words."""
    return [normalize(w) for _, _, w in word_spans(text)]
