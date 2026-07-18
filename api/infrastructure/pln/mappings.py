"""Mapeos entre el vocabulario de la DB (enum clínico) y el contrato de los
microservicios PLN. `Pln/` no se modifica: el backend traduce en ambos sentidos.

- DB enum subtype:  PHONOLOGICAL | VISUAL_SURFACE | MIXED | NO_DYSLEXIA
- PLN subtype RAW:  fonologico | visual | mixto | fluidez | sin_riesgo
- DB enum severity: MILD | MODERATE | SEVERE
- PLN severity RAW: leve | moderado | severo | ninguna
- DB risk_level:    LOW | MEDIUM | HIGH
- PLN risk_level:   bajo | medio | alto
"""
from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def pln_student_id(student_id: UUID | str) -> int:
    """UUID interno -> int estable que esperan los microservicios PLN.

    Los servicios 8001/8002 declaran student_id como int y solo lo reflejan en
    la respuesta (no lo usan para ML). Vive acá porque la derivación estaba
    duplicada en get_result.py y en intervention/router.py: si una copia
    cambiaba, el mismo alumno tendría IDs distintos entre /diagnose y
    /next-exercise.
    """
    return int(UUID(str(student_id)).hex[:8], 16)

# Código de módulo de batería (DB) -> nombre de módulo que entiende el Diagnosis Service.
MODULE_CODE_TO_PLN: dict[str, str] = {
    "M01_TEACHER_PRODISLEX_SCREENING": "conciencia_fonologica",  # docente; no suele mandarse como ítem
    "M02_PHONOLOGICAL_AWARENESS": "conciencia_fonologica",
    "M03_LETTERS_SYLLABLES": "lectura_voz_alta",
    "M04_REAL_WORDS": "palabras_reales",
    "M05_PSEUDOWORDS": "pseudopalabras",
    "M06_SMART_DICTATION": "dictado",
    "M07_CONTROLLED_COPY": "copia_controlada",
    "M08_RAPID_NAMING": "denominacion_rapida",
    "M09_READING_COMPREHENSION": "comprension_lectora",
}

# Subtipo RAW del PLN -> enum clínico de la DB. fluidez no es un subtipo clínico:
# se almacena como MIXED en la columna tipada, pero el valor RAW se conserva aparte
# y es el que se reenvía a /recommend.
PLN_SUBTYPE_TO_ENUM: dict[str, str] = {
    "fonologico": "PHONOLOGICAL",
    "visual": "VISUAL_SURFACE",
    "mixto": "MIXED",
    "fluidez": "MIXED",
    "comprension": "MIXED",
    "sin_riesgo": "NO_DYSLEXIA",
}

PLN_SEVERITY_TO_ENUM: dict[str, str | None] = {
    "leve": "MILD",
    "moderado": "MODERATE",
    "severo": "SEVERE",
    "ninguna": None,
    "": None,
}

PLN_RISK_TO_ENUM: dict[str, str] = {
    "bajo": "LOW",
    "medio": "MEDIUM",
    "alto": "HIGH",
}

# Subtipo RAW del PLN -> profile_code de intervention.route_templates (DB).
PLN_SUBTYPE_TO_ROUTE_PROFILE: dict[str, str] = {
    "fonologico": "fonologico",
    "visual": "visual_superficial",
    "mixto": "mixto",
    "fluidez": "fluidez",
    "comprension": "comprension",
}


# Los defaults de abajo existen para que un valor inesperado nunca tumbe un
# diagnóstico en curso, pero un default silencioso es peligroso en clínica: si
# el PLN renombra una clase, el backend seguiría guardando MIXED/LOW sin que
# nadie se entere. Por eso cada default deja rastro en el log.


def module_to_pln(module_code: str | None) -> str:
    mapped = MODULE_CODE_TO_PLN.get(module_code or "")
    if mapped is None:
        logger.warning(
            "Módulo '%s' no está en MODULE_CODE_TO_PLN; se envía al PLN como "
            "'palabras_reales'. Si es un módulo nuevo, agrégalo al mapeo.",
            module_code,
        )
        return "palabras_reales"
    return mapped


def subtype_to_enum(pln_subtype: str | None) -> str:
    key = (pln_subtype or "").lower().strip()
    mapped = PLN_SUBTYPE_TO_ENUM.get(key)
    if mapped is None:
        logger.warning(
            "Subtipo PLN desconocido '%s'; se guarda como MIXED. Revisa si el "
            "modelo cambió su vocabulario de clases.",
            pln_subtype,
        )
        return "MIXED"
    return mapped


def severity_to_enum(pln_severity: str | None) -> str | None:
    key = (pln_severity or "").lower().strip()
    if key not in PLN_SEVERITY_TO_ENUM:
        logger.warning("Severidad PLN desconocida '%s'; se guarda como NULL.", pln_severity)
        return None
    return PLN_SEVERITY_TO_ENUM[key]


def risk_to_enum(pln_risk: str | None) -> str:
    key = (pln_risk or "").lower().strip()
    mapped = PLN_RISK_TO_ENUM.get(key)
    if mapped is None:
        logger.warning(
            "Nivel de riesgo PLN desconocido '%s'; se guarda como LOW. OJO: un "
            "riesgo real podría estar subestimándose.",
            pln_risk,
        )
        return "LOW"
    return mapped


def subtype_to_route_profile(pln_subtype: str | None) -> str | None:
    return PLN_SUBTYPE_TO_ROUTE_PROFILE.get((pln_subtype or "").lower().strip())
