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

    fix_stt_artifacts solo se aplica cuando la respuesta REALMENTE vino de
    reconocimiento de voz (input_method == "stt"). Antes se aplicaba mirando
    únicamente el módulo, así que una respuesta escrita a mano por el alumno
    (p. ej. la letra "k" en un dictado) se "corregía" a "qu" antes de
    compararla contra el target, borrando un error potencialmente real.

    OJO sobre el alcance: fix_stt_artifacts hace lookup por palabra COMPLETA,
    así que hoy solo transforma respuestas que son exactamente "k", "q" o "x"
    — pese a que sus comentarios sugieren casos como "ke"->"que". Este gate
    por input_method es correcto igual, pero su efecto práctico es acotado
    mientras esa función no se corrija (cambiarla alteraría las features
    respecto a las del entrenamiento, así que no se toca acá).

    Si input_method no viene informado se conserva el comportamiento anterior
    (asumir STT en los módulos aplicables) para no romper clientes viejos.
    """
    text = preprocess(item.get("response", ""))
    if item.get("module") not in STT_APPLICABLE_MODULES:
        return text

    input_method = (item.get("input_method") or "").strip().lower()
    if input_method in ("", "stt"):
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
