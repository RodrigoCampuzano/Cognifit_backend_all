"""Las discrepancias de PRODISLEX distinguen una dificultad ESPECÍFICA de
lectura de una dificultad general de aprendizaje.

Un alumno que explica todo hablando y se derrumba al escribir tiene el patrón
clásico. Uno que rinde parejo y bajo en todo probablemente tenga otra cosa. Los
ocho ítems de sintomatología no distinguen esos dos casos: ambos marcarían
"lee lento" y "omite letras".
"""
from application.services.screening_service import ScreeningService


RIESGO = [
    {"item_code": "q01", "weight": 50, "tags": ["ROT"], "categoria": "RIESGO"},
    {"item_code": "q02", "weight": 50, "tags": ["OMI"], "categoria": "RIESGO"},
]
DISC = [
    {"item_code": f"d0{i}", "weight": 0, "tags": ["discrepancia"], "categoria": "DISCREPANCIA"}
    for i in range(1, 7)
]
ITEMS = RIESGO + DISC


def _resp(sintomas, disc):
    r = [{"item_code": "q01", "value": sintomas}, {"item_code": "q02", "value": sintomas}]
    r += [{"item_code": f"d0{i}", "value": disc} for i in range(1, 7)]
    return r


def test_separa_dos_perfiles_que_antes_eran_identicos():
    """Es la razón de existir del índice."""
    svc = ScreeningService()
    especifico = svc.calculate_teacher_score(ITEMS, _resp(1, 1))
    general = svc.calculate_teacher_score(ITEMS, _resp(1, 0))

    assert especifico["score"] == general["score"], "mismos síntomas"
    assert especifico["indice_discrepancia"] > general["indice_discrepancia"]


def test_no_altera_el_puntaje_de_sintomas():
    """Los ocho ítems de riesgo tienen pesos con fundamento y suman 100.
    Diluirlos correría el umbral de 50 que decide qué batería recibe el
    alumno, o sea cambiaría la prueba que se le aplica."""
    svc = ScreeningService()
    con = svc.calculate_teacher_score(ITEMS, _resp(1, 1))
    sin = svc.calculate_teacher_score(RIESGO, [
        {"item_code": "q01", "value": 1}, {"item_code": "q02", "value": 1}])
    assert con["score"] == sin["score"] == 100.0


def test_no_altera_que_bateria_se_asigna():
    svc = ScreeningService()
    for disc in (0, 0.5, 1):
        r = svc.calculate_teacher_score(ITEMS, _resp(0, disc))
        assert r["battery_mode"] == "QUICK", (
            "la discrepancia no debe decidir la batería por sí sola"
        )


def test_el_indice_va_de_cero_a_cien():
    svc = ScreeningService()
    assert svc.calculate_teacher_score(ITEMS, _resp(0, 0))["indice_discrepancia"] == 0.0
    assert svc.calculate_teacher_score(ITEMS, _resp(0, 1))["indice_discrepancia"] == 100.0
    assert svc.calculate_teacher_score(ITEMS, _resp(0, 0.5))["indice_discrepancia"] == 50.0


def test_sin_items_de_discrepancia_el_indice_es_none():
    """None y no 0: no es lo mismo "no se preguntó" que "se preguntó y no hay
    discrepancia". Un cero sugeriría que se descartó el patrón."""
    svc = ScreeningService()
    r = svc.calculate_teacher_score(RIESGO, [
        {"item_code": "q01", "value": 1}, {"item_code": "q02", "value": 1}])
    assert r["indice_discrepancia"] is None


def test_se_listan_las_discrepancias_marcadas():
    svc = ScreeningService()
    r = svc.calculate_teacher_score(ITEMS, _resp(0, 1))
    assert len(r["discrepancias"]) == 6
    assert all("discrepancia" in d["tags"] for d in r["discrepancias"])
