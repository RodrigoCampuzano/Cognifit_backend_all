from __future__ import annotations

import logging
from collections import Counter
from uuid import UUID

from application.services.risk_calculator import RiskCalculator
from infrastructure.database.repositories.pg_result_repository import PgResultRepository
from infrastructure.database.repositories.pg_session_repository import PgSessionRepository
from infrastructure.nlp.spacy_nlp_service import SpacyNlpService
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.errors import PlnServiceError
from infrastructure.pln.mappings import (
    module_to_pln,
    risk_to_enum,
    severity_to_enum,
    subtype_to_enum,
    subtype_to_route_profile,
)
from infrastructure.pln.recommendation_client import RecommendationServiceClient

logger = logging.getLogger(__name__)

_CAPTURE_TO_INPUT = {"stt": "stt", "voice": "stt", "audio": "stt", "typed": "teclado", "keyboard": "teclado", "teclado": "teclado", "touch": "tactil", "tactil": "tactil"}


def _pln_student_id(student_id: UUID | str) -> int:
    """El Diagnosis/Recommendation Service esperan student_id int (solo lo reflejan,
    no lo usan para ML). Derivamos un int estable del UUID interno."""
    hexs = UUID(str(student_id)).hex
    return int(hexs[:8], 16)


class GetResultUseCase:
    def __init__(
        self,
        sessions: PgSessionRepository,
        results: PgResultRepository,
        nlp: SpacyNlpService,
        risk: RiskCalculator,
        diagnosis_client: DiagnosisServiceClient | None = None,
        recommendation_client: RecommendationServiceClient | None = None,
        fallback_enabled: bool = True,
    ) -> None:
        self.sessions = sessions
        self.results = results
        self.nlp = nlp
        self.risk = risk
        self.diagnosis_client = diagnosis_client
        self.recommendation_client = recommendation_client
        self.fallback_enabled = fallback_enabled

    async def diagnose_session(self, session_id: UUID) -> dict:
        context = await self.sessions.get_session_context(session_id)
        if not context:
            raise ValueError("Session not found")

        # Acumular TODAS las respuestas del assignment (todas sus sesiones/módulos).
        responses = await self.sessions.get_assignment_responses(context["assignment_id"])
        if not responses:
            responses = await self.sessions.get_session_responses(session_id)

        breakdown: Counter[str] = Counter()
        for row in responses:
            breakdown.update(row.get("error_breakdown") or {})

        payload: dict | None = None
        feature_vector: list[float] | None = None

        if self.diagnosis_client is not None:
            try:
                payload, feature_vector = await self._diagnose_with_service(context, responses)
            except PlnServiceError as exc:
                if not self.fallback_enabled:
                    raise ValueError(f"Diagnosis Service no disponible: {exc.detail}") from exc
                logger.warning("Diagnosis Service falló (%s); usando pipeline local de respaldo.", exc.detail)

        if payload is None:
            payload, feature_vector = self._diagnose_locally(context, responses, breakdown)

        module_metrics = {"module_code": context["module_code"], "response_count": len(responses)}

        await self.sessions.complete_assignment_sessions(context["assignment_id"])
        saved = await self.results.save_diagnosis(
            context=context,
            result_payload=payload,
            feature_vector=feature_vector or [],
            error_breakdown=payload.get("error_breakdown") or dict(breakdown),
            module_metrics=module_metrics,
        )

        # Persistir la ruta (si el diagnóstico no es sin_riesgo y hay servicio de recomendación).
        student_path = None
        if payload.get("recommendation") is not None:
            route_profile = subtype_to_route_profile(payload.get("pln_subtype"))
            student_path = await self.results.save_student_path(
                student_id=context["student_id"],
                diagnosis_id=saved["id"],
                recommendation=payload["recommendation"],
                route_profile=route_profile,
            )
        saved["student_path"] = student_path
        saved["exercises"] = payload.get("recommended_route", [])
        return saved

    async def _diagnose_with_service(self, context: dict, responses: list[dict]) -> tuple[dict, list[float]]:
        items = []
        for row in responses:
            capture = (row.get("capture_modality") or "stt").lower()
            items.append(
                {
                    "target": row.get("expected_text") or "",
                    "response": row.get("raw_response") or "",
                    "module": module_to_pln(row.get("module_code")),
                    "response_time_ms": int(row.get("response_time_ms") or 0),
                    "input_method": _CAPTURE_TO_INPUT.get(capture, "stt"),
                }
            )
        if not items:
            raise PlnServiceError("diagnosis", "no hay respuestas para diagnosticar")

        diag_request = {
            "student_id": _pln_student_id(context["student_id"]),
            "grade": int(context.get("grade") or 3),
            "teacher_score": float(context.get("teacher_score") or 0.0),
            "session_number": 1,
            "items": items,
        }
        diag = await self.diagnosis_client.diagnose(diag_request)

        # Recomendación de ruta (valores RAW del PLN).
        recommendation = None
        recommended_route: list[str] = []
        recommendation_reason = ""
        if self.recommendation_client is not None and diag.get("subtype") != "sin_riesgo":
            try:
                recommendation = await self.recommendation_client.recommend(
                    {
                        "student_id": _pln_student_id(context["student_id"]),
                        "subtype": diag["subtype"],
                        "severity": diag["severity"],
                        "risk_probability": diag.get("risk_probability"),
                        "grade": int(context.get("grade") or 3),
                    }
                )
                recommended_route = [ex["exercise_id"] for ex in recommendation.get("exercises", [])]
                recommendation_reason = recommendation.get("message", "")
            except PlnServiceError as exc:
                logger.warning("Recommendation Service falló (%s); diagnóstico se guarda sin ruta.", exc.detail)

        payload = {
            "subtype": subtype_to_enum(diag["subtype"]),
            "severity": severity_to_enum(diag["severity"]),
            "pln_subtype": diag["subtype"],
            "pln_severity": diag["severity"],
            "risk_probability": diag["risk_probability"],
            "risk_level": risk_to_enum(diag.get("risk_level")),
            "main_error_codes": diag.get("main_error_codes", []),
            "error_breakdown": diag.get("error_breakdown", {}),
            "model_version": diag.get("model_version"),
            "pln_source": "service",
            "recommended_route": recommended_route,
            "recommendation_reason": recommendation_reason,
            "recommendation": recommendation,
        }
        feature_vector = diag.get("feature_vector") or []
        return payload, feature_vector

    def _diagnose_locally(self, context: dict, responses: list[dict], breakdown: Counter) -> tuple[dict, list[float]]:
        analyses = []
        for row in responses:
            analysis = dict(row)
            analysis["item_kind"] = row.get("item_kind") or row.get("module_code")
            analysis["error_breakdown"] = row.get("error_breakdown") or {}
            analyses.append(analysis)
        feature_vector = self.nlp.build_feature_vector(analyses, int(context.get("grade") or 3), float(context.get("teacher_score") or 0))
        module_metrics = {"module_code": context["module_code"], "response_count": len(responses)}
        classification = self.risk.classify(feature_vector, dict(breakdown), module_metrics)
        payload = {
            "subtype": classification.subtype,
            "severity": classification.severity,
            "pln_subtype": None,
            "pln_severity": None,
            "risk_probability": classification.risk_probability,
            "risk_level": classification.risk_level,
            "main_error_codes": classification.main_error_codes,
            "error_breakdown": dict(breakdown),
            "model_version": "pln-rule-v1-fallback",
            "pln_source": "local_fallback",
            "recommended_route": classification.recommended_route,
            "recommendation_reason": classification.recommendation_reason,
            "recommendation": None,
        }
        return payload, feature_vector
