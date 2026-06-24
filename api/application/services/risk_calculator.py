from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from domain.value_objects.risk_level import RiskLevel


FEATURE_NAMES = [
    "OMI_rate",
    "SUS_rate",
    "INV_rate",
    "ROT_rate",
    "LEX_rate",
    "SEG_rate",
    "UNI_rate",
    "FON_rate",
    "ADD_rate",
    "LEN_rate",
    "accuracy",
    "error_rate",
    "pseudo_vs_word_gap",
    "pseudo_error_rate",
    "word_error_rate",
    "avg_time_norm",
    "std_time_norm",
    "slow_response_rate",
    "avg_phonetic_sim",
    "avg_ngram_overlap",
    "rot_sus_ratio",
    "lex_flag",
    "seg_uni_rate",
    "inv_omi_ratio",
    "module_completion_rate_suggested",
    "dominant_error_concentration_suggested",
    "grade_norm",
    "teacher_score_norm",
]

ROUTES = {
    "PHONOLOGICAL": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1", "DIC_palabras_simples_N1"],
    "VISUAL_SURFACE": ["VIS_discriminacion_bd_N1", "VIS_memoria_palabras_N1", "DEN_rapid_letras_N1"],
    "MIXED": ["MULTI_silabas_cromaticas_N1", "MULTI_lectura_auditiva_N1", "CF_silabas_N1", "PS_cv_N1"],
    "FLUENCY": ["DEN_rapid_colores_N1", "LEC_repetida_N1", "LEC_temporizador_N1"],
    "COMPREHENSION": ["COMP_textos_cortos_N1", "apoyo_auditivo", "vocabulario_N1"],
    "NO_DYSLEXIA": [],
}


@dataclass(slots=True)
class RiskClassification:
    subtype: str
    severity: str | None
    risk_probability: float
    risk_level: str
    main_error_codes: list[str]
    recommended_route: list[str]
    recommendation_reason: str


class RiskCalculator:
    def classify(self, feature_vector: list[float], error_breakdown: dict, module_metrics: dict | None = None) -> RiskClassification:
        features = dict(zip(FEATURE_NAMES, feature_vector, strict=False))
        error_rate = features.get("error_rate", 0.0)
        teacher = features.get("teacher_score_norm", 0.0)
        pseudo_gap = features.get("pseudo_vs_word_gap", 0.0)
        pseudo_error = features.get("pseudo_error_rate", 0.0)
        word_error = features.get("word_error_rate", 0.0)
        rot = features.get("ROT_rate", 0.0)
        lex = features.get("LEX_rate", 0.0)
        fon = features.get("FON_rate", 0.0)
        inv = features.get("INV_rate", 0.0)
        len_rate = features.get("LEN_rate", 0.0)
        comprehension = float((module_metrics or {}).get("COM_rate", 0.0))

        risk = self._clamp(0.45 * error_rate + 0.25 * pseudo_error + 0.15 * teacher + 0.10 * pseudo_gap + 0.05 * len_rate)

        if risk < 0.20 and error_rate < 0.15:
            subtype = "NO_DYSLEXIA"
            reason = "Riesgo bajo con pocos errores acumulados."
        elif comprehension >= 0.35 and error_rate < 0.35:
            subtype = "COMPREHENSION"
            reason = "Lectura relativamente conservada con errores de comprension."
        elif len_rate >= 0.35 and error_rate < 0.30:
            subtype = "FLUENCY"
            reason = "Pocos errores de precision, pero lentitud dominante."
        elif pseudo_gap > 0.20 or (pseudo_error > word_error + 0.15 and (fon + inv) >= rot):
            subtype = "PHONOLOGICAL"
            reason = "Falla mas en pseudopalabras que en palabras reales; patron fonologico."
        elif pseudo_gap < 0.10 and (rot + lex) >= max(0.12, fon + inv):
            subtype = "VISUAL_SURFACE"
            reason = "Confusiones visuales/rotaciones y lexicalizacion dominantes."
        else:
            subtype = "MIXED"
            reason = "Falla amplia con mezcla de errores fonologicos y visuales."

        severity = None if subtype == "NO_DYSLEXIA" else self._severity(risk)
        public_subtype = subtype if subtype in {"PHONOLOGICAL", "VISUAL_SURFACE", "MIXED", "NO_DYSLEXIA"} else "MIXED"
        if subtype in {"FLUENCY", "COMPREHENSION"}:
            public_subtype = "MIXED"

        return RiskClassification(
            subtype=public_subtype,
            severity=severity,
            risk_probability=round(risk, 4),
            risk_level=RiskLevel.from_probability(risk).value,
            main_error_codes=self._top_error_codes(error_breakdown),
            recommended_route=ROUTES.get(subtype, ROUTES.get(public_subtype, [])),
            recommendation_reason=reason,
        )

    def _top_error_codes(self, error_breakdown: dict) -> list[str]:
        counter: Counter[str] = Counter()
        for code, value in error_breakdown.items():
            if isinstance(value, (int, float)):
                counter[code] += float(value)
            elif isinstance(value, list):
                counter[code] += len(value)
        return [code for code, _ in counter.most_common(5)]

    def _severity(self, probability: float) -> str:
        if probability >= 0.80:
            return "SEVERE"
        if probability >= 0.50:
            return "MODERATE"
        return "MILD"

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
