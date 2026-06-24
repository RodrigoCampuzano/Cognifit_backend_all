from __future__ import annotations

import re
import unicodedata

WORD_RE = re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", re.UNICODE)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", text).strip().lower()
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def tokenize(text: str | None) -> list[str]:
    return WORD_RE.findall(normalize_text(text))
