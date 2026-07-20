from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ANSWER_VALUES = {
    "nunca": Decimal("0"),
    "a veces": Decimal("0.5"),
    "aveces": Decimal("0.5"),
    "frecuente": Decimal("1"),
    "0": Decimal("0"),
    "0.0": Decimal("0"),
    "0.5": Decimal("0.5"),
    "1": Decimal("1"),
    "1.0": Decimal("1"),
}

QUICK_MODULES = [
    "M02_PHONOLOGICAL_AWARENESS",
    "M04_REAL_WORDS",
    "M08_RAPID_NAMING",
]

FULL_MODULES = [
    "M02_PHONOLOGICAL_AWARENESS",
    "M03_LETTERS_SYLLABLES",
    "M04_REAL_WORDS",
    "M05_PSEUDOWORDS",
    "M06_SMART_DICTATION",
    "M07_CONTROLLED_COPY",
    "M08_RAPID_NAMING",
    "M09_READING_COMPREHENSION",
    # Discriminación visual: la migración 009 creó el módulo completo (test,
    # 21 ítems) pero nunca se agregó acá, así que ningún alumno lo recibía.
    # Es la señal directa del subtipo visual (confusión b/d, p/q).
    "M10_VD",
]


class ScreeningService:
    def normalize_answer_value(self, value: Any) -> Decimal:
        if isinstance(value, (int, float, Decimal)):
            key = str(value).lower()
        else:
            key = str(value).strip().lower()
        if key not in ANSWER_VALUES:
            raise ValueError(f"Invalid answer value: {value!r}")
        return ANSWER_VALUES[key]

    def calculate_teacher_score(self, items: list[dict], answers: list[dict]) -> dict:
        answer_map = {str(a["item_code"]): a["value"] for a in answers}
        weighted = Decimal("0")
        total_weight = Decimal("0")
        flags: list[dict] = []

        alertas_clinicas: list[dict] = []

        for item in items:
            code = str(item.get("item_code"))
            if code not in answer_map:
                raise ValueError(f"Missing answer for {code}")
            value = self.normalize_answer_value(answer_map[code])

            # La historia clínica NO suma riesgo: no indica dislexia, indica
            # una explicación alternativa. Sumarla haría subir el puntaje de un
            # alumno cuya dificultad quizá se explique por no ver bien, que es
            # exactamente lo contrario de lo que significa la respuesta.
            if item.get("categoria") == "HISTORIA_CLINICA":
                if value >= Decimal("0.5"):
                    alertas_clinicas.append({
                        "item_code": code,
                        "tags": item.get("tags", []),
                        "value": float(value),
                        # 0.5 es "No lo sé": se distingue de un sí rotundo
                        # porque pide comprobar, no concluir.
                        "certeza": "confirmado" if value >= Decimal("1") else "por_confirmar",
                    })
                continue

            weight = Decimal(str(item.get("weight", 0)))
            weighted += value * weight
            total_weight += weight
            if value >= Decimal("0.5"):
                flags.append({"item_code": code, "tags": item.get("tags", []), "value": float(value)})

        score = weighted if total_weight == Decimal("100") else (weighted * Decimal("100") / total_weight)
        score = score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Una causa sensorial sin corregir invalida la interpretación del
        # tamizaje: el protocolo define la dislexia como dificultad lectora
        # "en ausencia de alteraciones neurológicas y/o sensoriales que lo
        # justifiquen". Se señala aparte para que el resultado no se lea como
        # un diagnóstico cerrado.
        sensorial = [
            a for a in alertas_clinicas
            if {"vision", "audicion"} & set(a.get("tags") or [])
        ]

        return {
            "score": float(score),
            "battery_mode": "FULL" if score >= Decimal("50") else "QUICK",
            "enabled_module_codes": self.enabled_modules(float(score)),
            "risk_flags": flags,
            "alertas_clinicas": alertas_clinicas,
            "requiere_descartar_sensorial": bool(sensorial),
        }

    def enabled_modules(self, teacher_score: float) -> list[str]:
        return FULL_MODULES if teacher_score >= 50 else QUICK_MODULES
