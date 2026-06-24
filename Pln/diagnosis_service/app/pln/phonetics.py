"""
Análisis fonético (Metaphone) y similitud estructural (n-gramas).
"""
from metaphone import doublemetaphone


def phonetic_similarity(w1: str, w2: str) -> float:
    """
    Similitud fonética entre 0.0 y 1.0.
    1.0 = suenan idéntico (error de escritura fonológico).
    Bajo = suenan diferente (error visual o de reconocimiento).
    """
    c1 = set(doublemetaphone(w1)) - {None, ""}
    c2 = set(doublemetaphone(w2)) - {None, ""}
    if c1 & c2:
        return 1.0
    union = c1 | c2
    return len(c1 & c2) / len(union) if union else 0.0


def extract_char_ngrams(word: str, n: int = 2) -> list:
    """Extrae n-gramas de caracteres de una palabra."""
    return [word[i:i + n] for i in range(len(word) - n + 1)]


def ngram_overlap(target: str, response: str, n: int = 2) -> float:
    """Fracción de n-gramas del target presentes en la respuesta."""
    tg = set(extract_char_ngrams(target, n))
    rg = set(extract_char_ngrams(response, n))
    if not tg:
        return 0.0
    return len(tg & rg) / len(tg)
