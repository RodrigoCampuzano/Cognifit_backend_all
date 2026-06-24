"""
Preprocesamiento de texto del alumno.
Limpia y normaliza la respuesta antes de compararla con el target.
"""
import re
import unicodedata

# Correcciones de artefactos comunes del STT en español mexicano
STT_CORRECTIONS = {
    "k": "qu",   # "ke" -> "que"
    "q": "qu",   # "qiero" -> "quiero"
    "x": "j",    # "xente" -> "gente" (arcaísmo)
}

# Módulos donde aplica la corrección STT.
# En "copia_controlada" se evalúa exactamente lo escrito -> NO corregir.
STT_APPLICABLE_MODULES = {
    "dictado", "palabras_reales", "pseudopalabras", "lectura_voz_alta",
}

TIMEOUT_THRESHOLD_MS = 15_000


def preprocess(text: str) -> str:
    """Normaliza un texto: minúsculas, unicode NFC, sin puntuación, espacios colapsados."""
    if text is None:
        return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFC", text)
    # Eliminar puntuación pero conservar letras y acentos del español
    text = re.sub(r"[^\w\sáéíóúüñ]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fix_stt_artifacts(text: str) -> str:
    """Corrige artefactos frecuentes del STT en español MX (solo módulos aplicables)."""
    words = text.split()
    return " ".join(STT_CORRECTIONS.get(w, w) for w in words)


def preprocess_item(item: dict) -> str:
    """
    Preprocesa la respuesta de un ítem.
    Aplica fix_stt_artifacts solo en los módulos donde corresponde.
    """
    text = preprocess(item.get("response", ""))
    if item.get("module") in STT_APPLICABLE_MODULES:
        text = fix_stt_artifacts(text)
    return text


def handle_timeout(item: dict) -> dict:
    """
    Detecta y marca ítems sin respuesta (timeout).
    Un timeout se trata como omisión total (OMI) y se excluye del cálculo de tiempos.
    """
    response = str(item.get("response", "") or "").strip()
    is_timeout = (
        not response or
        item.get("response_time_ms", 0) >= TIMEOUT_THRESHOLD_MS
    )
    if is_timeout:
        return {
            **item,
            "response": "",
            "is_correct": False,
            "is_timeout": True,
            "errors": [{
                "type": "OMI",
                "expected_char": item.get("target", ""),
                "position": 0,
                "context": item.get("target", ""),
                "detail": "sin_respuesta_timeout",
                "is_diagnostic": True,
            }],
            "phonetic_similarity": 0.0,
            "ngram_overlap": 0.0,
        }
    return {**item, "is_timeout": False}
