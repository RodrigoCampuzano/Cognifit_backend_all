from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ANSWER_VALUES = {
    "nunca": Decimal("0"),
    "a veces": Decimal("0.5"),
    "aveces": Decimal("0.5"),
    "frecuente": Decimal("1"),
    "0": Decimal("0"),
    "0.5": Decimal("0.5"),
    "1": Decimal("1"),
}

QUICK_MODULES = [
    "M02_PHONOLOGICAL_AWARENESS",
    "M04_REAL_WORDS",
    "M08_RAPID_NAMING",
]

FULL_MODULES = [
    "M01_TEACHER_PRODISLEX_SCREENING",
    "M02_PHONOLOGICAL_AWARENESS",
    "M03_LETTERS_SYLLABLES",
    "M04_REAL_WORDS",
    "M05_PSEUDOWORDS",
    "M06_SMART_DICTATION",
    "M07_CONTROLLED_COPY",
    "M08_RAPID_NAMING",
    "M09_READING_COMPREHENSION",
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

        for item in items:
            code = str(item.get("item_code"))
            if code not in answer_map:
                raise ValueError(f"Missing answer for {code}")
            weight = Decimal(str(item.get("weight", 0)))
            value = self.normalize_answer_value(answer_map[code])
            weighted += value * weight
            total_weight += weight
            if value >= Decimal("0.5"):
                flags.append({"item_code": code, "tags": item.get("tags", []), "value": float(value)})

        score = weighted if total_weight == Decimal("100") else (weighted * Decimal("100") / total_weight)
        score = score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "score": float(score),
            "battery_mode": "FULL" if score >= Decimal("50") else "QUICK",
            "enabled_module_codes": self.enabled_modules(float(score)),
            "risk_flags": flags,
        }

    def enabled_modules(self, teacher_score: float) -> list[str]:
        return FULL_MODULES if teacher_score >= 50 else QUICK_MODULES
