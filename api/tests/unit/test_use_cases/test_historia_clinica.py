"""La historia clínica de PRODISLEX descarta causas alternativas.

La definición de dislexia que usa el propio protocolo dice: dificultad
significativa en lectura y escritura "en ausencia de alteraciones neurológicas
y/o sensoriales que lo justifiquen".

Descartar una causa sensorial no es contexto: es parte de la definición. Un
niño que no ve bien el pizarrón lee mal y no es disléxico. El cuestionario
tenía solo los 8 ítems de sintomatología lectora, así que la aplicación podía
emitir "fonológico severo" para un alumno que necesita lentes.
"""
from decimal import Decimal

import pytest

from application.services.screening_service import ScreeningService


ITEMS = [
    {"item_code": "q01", "weight": 50, "tags": ["ROT"], "categoria": "RIESGO"},
    {"item_code": "q02", "weight": 50, "tags": ["OMI"], "categoria": "RIESGO"},
    {"item_code": "h01_vision", "weight": 0, "tags": ["sensorial", "vision"],
     "categoria": "HISTORIA_CLINICA"},
    {"item_code": "h02_audicion", "weight": 0, "tags": ["sensorial", "audicion"],
     "categoria": "HISTORIA_CLINICA"},
    {"item_code": "h05_antecedentes", "weight": 0, "tags": ["antecedente_familiar"],
     "categoria": "HISTORIA_CLINICA"},
]


def _resp(**kwargs):
    base = {"q01": 0, "q02": 0, "h01_vision": 0, "h02_audicion": 0, "h05_antecedentes": 0}
    base.update(kwargs)
    return [{"item_code": k, "value": v} for k, v in base.items()]


def test_la_historia_clinica_no_altera_el_puntaje():
    """Es lo central: estos ítems no indican dislexia sino una explicación
    alternativa. Si sumaran, un alumno que no ve bien tendría MÁS riesgo, que
    es exactamente lo contrario de lo que significa la respuesta."""
    svc = ScreeningService()
    sin = svc.calculate_teacher_score(ITEMS, _resp(q01=1, q02=1))
    con = svc.calculate_teacher_score(
        ITEMS, _resp(q01=1, q02=1, h01_vision=1, h02_audicion=1, h05_antecedentes=1)
    )
    assert sin["score"] == con["score"]


def test_una_alteracion_visual_pide_descartar_antes_de_concluir():
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, q02=1, h01_vision=1))
    assert r["requiere_descartar_sensorial"] is True


def test_una_alteracion_auditiva_tambien():
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, h02_audicion=1))
    assert r["requiere_descartar_sensorial"] is True


def test_un_antecedente_familiar_no_es_causa_alternativa():
    """El antecedente familiar es un factor de riesgo, no una explicación que
    invalide el tamizaje: se registra como alerta pero no exige descartar."""
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, h05_antecedentes=1))
    assert r["requiere_descartar_sensorial"] is False
    assert any(a["item_code"] == "h05_antecedentes" for a in r["alertas_clinicas"])


def test_no_lo_se_se_distingue_de_un_si():
    """El formulario en papel tiene una tercera columna, SE (sin evidencias,
    se necesita más observación). Obligar a elegir entre sí y no cuando no se
    sabe produce un dato inventado; acá la diferencia se conserva."""
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, h01_vision=0.5))
    alerta = next(a for a in r["alertas_clinicas"] if a["item_code"] == "h01_vision")
    assert alerta["certeza"] == "por_confirmar"

    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, h01_vision=1))
    alerta = next(a for a in r["alertas_clinicas"] if a["item_code"] == "h01_vision")
    assert alerta["certeza"] == "confirmado"


def test_sin_alteraciones_no_hay_alerta():
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, q02=1))
    assert r["alertas_clinicas"] == []
    assert r["requiere_descartar_sensorial"] is False


def test_los_items_de_riesgo_siguen_sumando_cien():
    """Excluir la historia clínica no debe alterar la normalización del
    puntaje: los de riesgo siguen definiendo la escala completa."""
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(q01=1, q02=1, h01_vision=1))
    assert r["score"] == 100.0
