from __future__ import annotations

import asyncio
import logging
from collections import Counter
from uuid import UUID

from application.services.risk_calculator import RiskCalculator
from infrastructure.database.repositories.pg_result_repository import PgResultRepository
from infrastructure.database.repositories.pg_session_repository import PgSessionRepository
from infrastructure.nlp.spacy_nlp_service import SpacyNlpService
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.errors import PlnServiceError
from application.services.alert_observer import create_alert_on_high_risk
from infrastructure.pln.mappings import (
    module_to_pln,
    pln_student_id,
    risk_to_enum,
    severity_to_enum,
    subtype_to_enum,
    subtype_to_route_profile,
)
from infrastructure.pln.recommendation_client import RecommendationServiceClient

logger = logging.getLogger(__name__)

# Techo de tiempo para la llamada opcional al Recommendation Service. El
# diagnóstico ya está listo cuando se hace, así que no debe alargar el request
# mucho más allá de lo que el alumno tolera esperando en pantalla.
RECOMMENDATION_BUDGET_SECONDS = 6.0

_CAPTURE_TO_INPUT = {"stt": "stt", "voice": "stt", "audio": "stt", "typed": "teclado", "keyboard": "teclado", "teclado": "teclado", "touch": "tactil", "tactil": "tactil"}

# Techo del tiempo de respuesta que se manda al Diagnosis Service.
#
# MITIGACIÓN, no solución definitiva. Los modelos actuales pesan muchísimo el
# tiempo de respuesta y se entrenaron sobre todo con tareas de LECTURA (leer una
# palabra = 1-2 s). En tareas de razonamiento (conciencia fonológica,
# comprensión) 4-8 s es normal, pero el modelo lo interpreta como lentitud
# patológica: un alumno que responde TODO BIEN pero pensando sale con riesgo
# alto (subtipo "visual"). El efecto se dispara cuando se diagnostica con un
# solo módulo, porque sin tareas de lectura el tiempo queda como única señal.
#
# Acotar el tiempo a este techo evita que una respuesta lenta pero correcta
# domine el vector. Se mantiene por debajo del umbral de "lento" (5000 ms) del
# feature engineering para que ningún ítem se marque como slow_response.
#
# La solución real es diagnosticar con la batería completa (no módulo por
# módulo) y/o reentrenar con tiempos por tipo de tarea; ver get_result §A.
_MAX_RESPONSE_TIME_MS = 4000


def _edad_desde_anio(birth_year) -> int | None:
    """Edad aproximada a partir del año de nacimiento.

    Aproximada a propósito: no se guarda la fecha completa, así que el error
    es de hasta un año. Para elegir una fila del baremo del TEDE —que va de 6
    a 10 años— alcanza, y el servicio ya toma la fila más cercana.
    """
    try:
        anio = int(birth_year)
    except (TypeError, ValueError):
        return None
    from datetime import date
    edad = date.today().year - anio
    return edad if 5 <= edad <= 13 else None


def _pln_student_id(student_id: UUID | str) -> int:
    """Alias del helper compartido en infrastructure.pln.mappings.

    La derivación vive allá para que /diagnose, /recommend y /next-exercise
    usen exactamente la misma, en vez de tener copias que puedan divergir.
    """
    return pln_student_id(student_id)


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
                    # Se propaga tal cual (no como ValueError) para que el router
                    # lo traduzca a 503: antes se convertía en ValueError y el
                    # `except ValueError` del router lo devolvía como 404, o sea
                    # indistinguible de "la sesión no existe".
                    raise
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

        # Avisar al docente si el tamizaje salió en riesgo alto. Va en la misma
        # transacción que el diagnóstico (si algo falla, no queda una alerta
        # huérfana apuntando a un diagnóstico que no se guardó).
        try:
            saved["alert"] = await create_alert_on_high_risk(
                self.results.session,
                student_id=context["student_id"],
                pln_subtype=payload.get("pln_subtype"),
                pln_severity=payload.get("pln_severity"),
                risk_level=saved.get("risk_level") or payload.get("risk_level"),
                risk_probability=payload.get("risk_probability"),
            )
        except Exception:
            # La alerta es un aviso, no parte del diagnóstico: si falla se
            # registra pero no se pierde el diagnóstico ya calculado.
            logger.exception("No se pudo crear la alerta de riesgo alto (student=%s)", context["student_id"])
            saved["alert"] = None
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
                    "response_time_ms": min(int(row.get("response_time_ms") or 0), _MAX_RESPONSE_TIME_MS),
                    "input_method": _CAPTURE_TO_INPUT.get(capture, "stt"),
                    # difficulty vive en la DB desde siempre pero nunca se
                    # enviaba. El modelo actual no la usa (no está entre sus 28
                    # features), pero sin mandarla el reentrenamiento tampoco
                    # podría usarla: el servicio la acepta y la ignora por ahora.
                    "difficulty_level": int(row.get("difficulty") or 1),
                    # Identifica a qué subtest del TEDE pertenece el ítem: el
                    # baremo de Errores Específicos se calcula sobre 71 ítems
                    # concretos, no sobre los códigos de error.
                    "item_code": row.get("item_code"),
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
        # El TEDE tiene baremos por edad además de por curso, y son tablas
        # distintas: un alumno repetidor de 9 años en 2º no se compara igual
        # contra su curso que contra su edad. Se manda cuando se puede
        # calcular; el servicio usa solo la de grado si falta.
        edad = _edad_desde_anio(context.get("birth_year"))
        if edad is not None:
            diag_request["age"] = edad
        diag = await self.diagnosis_client.diagnose(diag_request)

        # Recomendación de ruta (valores RAW del PLN).
        recommendation = None
        recommended_route: list[str] = []
        recommendation_reason = ""
        if self.recommendation_client is not None and diag.get("subtype") != "sin_riesgo":
            try:
                # La ruta es un extra: su fallo ya se traga más abajo y el
                # diagnóstico se guarda igual. Por eso se le pone un techo de
                # tiempo propio, más corto que el del diagnóstico: sin esto,
                # con el servicio de recomendación colgado el alumno se quedaba
                # mirando la pantalla ~10s extra DESPUÉS de que su diagnóstico
                # ya estaba listo, y el request completo podía irse a ~30s.
                recommendation = await asyncio.wait_for(
                    self.recommendation_client.recommend(
                        {
                            "student_id": _pln_student_id(context["student_id"]),
                            "subtype": diag["subtype"],
                            "severity": diag["severity"],
                            "risk_probability": diag.get("risk_probability"),
                            "grade": int(context.get("grade") or 3),
                        }
                    ),
                    timeout=RECOMMENDATION_BUDGET_SECONDS,
                )
                recommended_route = [ex["exercise_id"] for ex in recommendation.get("exercises", [])]
                recommendation_reason = recommendation.get("message", "")
            except asyncio.TimeoutError:
                logger.warning(
                    "Recommendation Service excedió %ss; diagnóstico se guarda sin ruta.",
                    RECOMMENDATION_BUDGET_SECONDS,
                )
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
            # Percentil normativo del TEDE, al lado de la severidad del modelo.
            # Viene None cuando la sesión no tuvo ítems de lectura de letras y
            # sílabas, y también cuando el diagnóstico salió del respaldo local
            # —ese camino no calcula baremo—, así que su ausencia distingue por
            # sí sola un diagnóstico respaldado de uno completo.
            "tede_nivel_lector": diag.get("tede_nivel_lector"),
            "tede_errores_especificos": diag.get("tede_errores_especificos"),
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
