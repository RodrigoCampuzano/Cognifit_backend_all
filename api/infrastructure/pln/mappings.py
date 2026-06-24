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


def module_to_pln(module_code: str | None) -> str:
    return MODULE_CODE_TO_PLN.get(module_code or "", "palabras_reales")


def subtype_to_enum(pln_subtype: str | None) -> str:
    return PLN_SUBTYPE_TO_ENUM.get((pln_subtype or "").lower().strip(), "MIXED")


def severity_to_enum(pln_severity: str | None) -> str | None:
    return PLN_SEVERITY_TO_ENUM.get((pln_severity or "").lower().strip(), None)


def risk_to_enum(pln_risk: str | None) -> str:
    return PLN_RISK_TO_ENUM.get((pln_risk or "").lower().strip(), "LOW")


def subtype_to_route_profile(pln_subtype: str | None) -> str | None:
    return PLN_SUBTYPE_TO_ROUTE_PROFILE.get((pln_subtype or "").lower().strip())
