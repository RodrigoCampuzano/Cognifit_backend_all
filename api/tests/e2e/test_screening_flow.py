"""Flujo de tamizaje: submit -> diagnose -> lectura del resultado.

Este archivo era un `assert True`. Se reemplaza por pruebas que ejercitan la
orquestación real de GetResultUseCase con dobles de prueba, cubriendo
justamente los caminos que se rompieron en producción:

- el fallback local cuando el Diagnosis Service no responde;
- la propagación de PlnServiceError (para que el router devuelva 503 y no un
  404 indistinguible de "sesión no existe") cuando el fallback está apagado;
- que la asignación se cierre al terminar (antes quedaba PENDING de por vida).

No toca la base ni la red: el objetivo es fijar el contrato entre las piezas.
"""
import asyncio
from uuid import uuid4

import pytest

from application.use_cases.screening.get_result import GetResultUseCase
from infrastructure.pln.errors import PlnServiceError


class _Sessions:
    """Doble de PgSessionRepository."""

    def __init__(self, responses=None):
        self.student_id = uuid4()
        self.assignment_id = uuid4()
        self._responses = responses if responses is not None else [
            {
                "expected_text": "casa", "raw_response": "caza",
                "module_code": "M06_SMART_DICTATION", "response_time_ms": 3000,
                "capture_modality": "stt", "error_breakdown": {"SUS": 1},
                "is_correct": False,
            }
        ]
        self.completed: list = []

    async def get_session_context(self, session_id):
        return {
            "student_id": self.student_id, "assignment_id": self.assignment_id,
            "module_code": "M06_SMART_DICTATION", "grade": 3, "teacher_score": 70.0,
        }

    async def get_assignment_responses(self, assignment_id):
        return self._responses

    async def get_session_responses(self, session_id):
        return self._responses

    async def complete_assignment_sessions(self, assignment_id):
        self.completed.append(assignment_id)


class _AlertSession:
    """Sesión mínima para la alerta: no hay docente, así que no crea nada."""

    async def execute(self, statement, params=None):
        class _R:
            def first(self):
                return None

            def mappings(self):
                raise AssertionError("no debería insertar sin docente")

        return _R()


class _Results:
    """Doble de PgResultRepository."""

    def __init__(self):
        self.session = _AlertSession()
        self.saved = None

    async def get_or_create_rule_model(self):
        return str(uuid4())

    async def save_diagnosis(self, *, context, result_payload, feature_vector, error_breakdown, module_metrics):
        self.saved = {
            "id": uuid4(),
            "risk_level": result_payload.get("risk_level"),
            "pln_source": result_payload.get("pln_source"),
            "pln_subtype": result_payload.get("pln_subtype"),
        }
        return dict(self.saved)

    async def save_student_path(self, **kwargs):
        return {"id": uuid4()}


class _Nlp:
    """Doble de SpacyNlpService: solo se usa build_feature_vector en el fallback."""

    def build_feature_vector(self, analyses, grade, teacher_score):
        return [0.0] * 28


class _Risk:
    """Doble de RiskCalculator: devuelve una clasificación fija y verificable."""

    def classify(self, feature_vector, breakdown, module_metrics):
        class _C:
            subtype = "PHONOLOGICAL"
            severity = "MODERATE"
            risk_probability = 0.72
            risk_level = "HIGH"
            main_error_codes = ["SUS"]
            recommended_route = []
            recommendation_reason = ""

        return _C()


class _DiagnosisClientCaido:
    async def diagnose(self, payload):
        raise PlnServiceError("diagnosis", "connection refused", 503)


def _use_case(sessions, results, *, diagnosis_client=None, fallback_enabled=True):
    return GetResultUseCase(
        sessions, results, _Nlp(), _Risk(),
        diagnosis_client=diagnosis_client,
        recommendation_client=None,
        fallback_enabled=fallback_enabled,
    )


def test_diagnostica_con_fallback_local_si_el_servicio_pln_esta_caido():
    sessions, results = _Sessions(), _Results()
    uc = _use_case(sessions, results, diagnosis_client=_DiagnosisClientCaido())

    out = asyncio.run(uc.diagnose_session(uuid4()))

    assert out["pln_source"] == "local_fallback", "debe degradar al pipeline local, no fallar"
    assert sessions.completed == [sessions.assignment_id], "la asignación debe quedar cerrada"


def test_propaga_pln_service_error_si_el_fallback_esta_apagado():
    """El router lo traduce a 503. Antes se convertía en ValueError y salía
    como 404, indistinguible de 'la sesión no existe'."""
    uc = _use_case(_Sessions(), _Results(),
                   diagnosis_client=_DiagnosisClientCaido(), fallback_enabled=False)

    with pytest.raises(PlnServiceError):
        asyncio.run(uc.diagnose_session(uuid4()))


def test_sesion_inexistente_sigue_siendo_value_error():
    class _SinContexto(_Sessions):
        async def get_session_context(self, session_id):
            return None

    uc = _use_case(_SinContexto(), _Results())
    with pytest.raises(ValueError, match="Session not found"):
        asyncio.run(uc.diagnose_session(uuid4()))
