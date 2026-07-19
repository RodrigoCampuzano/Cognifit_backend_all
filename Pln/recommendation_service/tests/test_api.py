"""
Tests del Recommendation Service.
Ejecutar con: pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["exercises_loaded"] > 0


def test_list_routes():
    with TestClient(app) as client:
        r = client.get("/routes")
        assert r.status_code == 200
        routes = r.json()
        assert "fonologico/leve" in routes
        assert "visual/moderado" in routes
        assert "mixto/severo" in routes
        assert "fluidez/leve" in routes


def test_recommend_fonologico_leve():
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 21, "subtype": "fonologico",
            "severity": "leve", "grade": 2,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["subtype"] == "fonologico"
        assert data["total_exercises"] > 0
        ids = [e["exercise_id"] for e in data["exercises"]]
        assert "CF_silabas_N1" in ids
        # Orden correcto: conciencia fonológica antes que pseudopalabras
        assert ids.index("CF_silabas_N1") < ids.index("PS_cv_N1")


def test_recommend_visual_moderado():
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 5, "subtype": "visual",
            "severity": "moderado", "grade": 3,
        })
        assert r.status_code == 200
        data = r.json()
        ids = [e["exercise_id"] for e in data["exercises"]]
        assert "VIS_discriminacion_bd_N1" in ids
        assert "VIS_discriminacion_pq_N1" in ids


def test_recommend_mixto_severo():
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 7, "subtype": "mixto", "severity": "severo",
        })
        assert r.status_code == 200
        data = r.json()
        ids = [e["exercise_id"] for e in data["exercises"]]
        # Mixto severo debe tener ejercicios multimodales primero
        assert ids[0] == "MULTI_silabas_cromaticas_N1"
        assert len(ids) >= 8


def test_recommend_sin_riesgo():
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 3, "subtype": "sin_riesgo", "severity": "ninguna",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_exercises"] == 0
        assert "monitoreo" in data["message"].lower()


def test_recommend_invalid_subtype():
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 1, "subtype": "desconocido", "severity": "leve",
        })
        assert r.status_code == 404


def test_exercises_are_enriched():
    """Los ejercicios deben tener título y tipo del banco."""
    with TestClient(app) as client:
        r = client.post("/recommend", json={
            "student_id": 21, "subtype": "fonologico", "severity": "leve",
        })
        assert r.status_code == 200
        first = r.json()["exercises"][0]
        assert first["titulo"] is not None
        assert first["tipo"] is not None
        assert first["order"] == 1


def test_get_exercise_detail():
    with TestClient(app) as client:
        r = client.get("/exercises/CF_silabas_N1")
        assert r.status_code == 200
        data = r.json()
        assert data["exercise_id"] == "CF_silabas_N1"
        assert "items" in data


def test_get_exercise_not_found():
    with TestClient(app) as client:
        r = client.get("/exercises/EJERCICIO_QUE_NO_EXISTE")
        assert r.status_code == 404


def test_next_exercise_start():
    """Sin historial debe devolver el primer ejercicio."""
    with TestClient(app) as client:
        r = client.post("/next-exercise", json={
            "student_id": 21,
            "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
            "session_history": [],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["exercise_id"] == "CF_silabas_N1"
        assert data["action"] == "start"


def test_next_exercise_level_up():
    """Con 3 sesiones > 90% debe subir de nivel."""
    with TestClient(app) as client:
        r = client.post("/next-exercise", json={
            "student_id": 21,
            "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
            "session_history": [
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.95},
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.92},
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.91},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["exercise_id"] == "CF_fonema_inicial_N1"
        assert data["action"] == "level_up"


def test_next_exercise_add_support():
    """Con 3 sesiones < 40% debe activar soporte TTS."""
    with TestClient(app) as client:
        r = client.post("/next-exercise", json={
            "student_id": 21,
            "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1"],
            "session_history": [
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.30},
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.25},
                {"exercise_id": "CF_silabas_N1", "accuracy": 0.20},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "add_support"
        assert data["support"] == "tts_enabled"


# ─── Vía universal de comprensión ────────────────────────────────────────────
# Se entrega por grado y NO por perfil diagnóstico. Estas pruebas fijan esa
# separación: es justo lo que se rompería si alguien "simplifica" metiendo los
# ejercicios de comprensión en LEARNING_ROUTES.

def test_comprension_6to_tiene_contenido():
    with TestClient(app) as client:
        r = client.get("/comprehension/6")
        assert r.status_code == 200
        data = r.json()
        assert data["via"] == "universal_grado"
        assert data["total"] == 7, "6º debe tener los 7 ejercicios de comprensión"
        assert all(e["total_preguntas"] > 0 for e in data["exercises"])


def test_cobertura_de_4to_a_6to():
    # El ciclo alto era el hueco: 4º tenía 4 ejercicios, 5º dos y 6º ninguno.
    with TestClient(app) as client:
        for grado in ("4", "5", "6"):
            data = client.get(f"/comprehension/{grado}").json()
            assert data["total"] == 7, f"{grado}º debería tener 7 ejercicios"
            subtipos = {e["subtipo"] for e in data["exercises"]}
            assert len(subtipos) == 7, f"{grado}º repite habilidad: {subtipos}"


def test_grado_sin_contenido_responde_200_vacio():
    # No es un error: significa "todavía no hay material para ese grado".
    with TestClient(app) as client:
        r = client.get("/comprehension/1")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["grados_con_contenido"] == ["4", "5", "6"]


def test_comprension_no_entra_en_rutas_diagnosticas():
    # Un ejercicio de comprensión no debe alcanzarse por (subtipo, severidad):
    # el tamizaje no mide comprensión, así que ningún perfil lo predice.
    from app.routes import LEARNING_ROUTES
    ids_en_rutas = {eid for ruta in LEARNING_ROUTES.values() for eid in ruta}
    assert not any(
        eid.startswith(("COMP4_", "COMP5_", "COMP6_")) for eid in ids_en_rutas
    )


def test_detalle_de_comprension_trae_texto_e_items():
    with TestClient(app) as client:
        r = client.get("/exercises/COMP6_verificar_afirmaciones_N1")
        assert r.status_code == 200
        ex = r.json()
        assert ex["texto"].strip(), "sin texto el ejercicio no se puede jugar"
        # El esquema {estimulo, opciones, correcta} es el que ChoicePlayer ya
        # sabe leer en Flutter; si cambia, la pantalla deja de renderizar.
        for item in ex["items"]:
            assert item["correcta"] in item["opciones"]


# ─── Ruteo por grado ─────────────────────────────────────────────────────────
# `build_route` agrega el eje que faltaba: hasta ahora la ruta dependía solo de
# (subtipo, severidad) y un alumno de 6º recibía material de 1º-2º.

from app.routes import build_route, get_route, ROUTE_BUDGET

# Banco mínimo de prueba: no se usa el real para que estas pruebas no cambien
# de resultado cada vez que se agrega un ejercicio al banco.
_BANCO = {
    # Los de la ruta curada de (fonologico, leve), todos de grados bajos.
    "CF_silabas_N1":          {"grados": ["1", "2"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    "CF_fonema_inicial_N1":   {"grados": ["1", "2"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    "CF_rima_N1":             {"grados": ["1", "2"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    "PS_cv_N1":               {"grados": ["1", "2"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    "DIC_palabras_simples_N1": {"grados": ["1", "2"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    # Ejercicios de 6º que NINGUNA ruta menciona: el caso que motiva el cambio.
    "NUEVO_6to_a": {"grados": ["6"], "perfil_objetivo": ["fonologico"], "nivel": 2},
    "NUEVO_6to_b": {"grados": ["6"], "perfil_objetivo": ["fonologico"], "nivel": 1},
    # De otro perfil: no debe colarse.
    "OTRO_PERFIL": {"grados": ["6"], "perfil_objetivo": ["visual"], "nivel": 1},
    # Vía universal: nunca entra a una ruta diagnóstica.
    "COMP6_x": {"grados": ["6"], "perfil_objetivo": ["universal"], "nivel": 1,
                "via": "universal_grado"},
}


def test_alumno_de_6to_recibe_ejercicios_de_su_grado():
    ruta, cubre = build_route("fonologico", "leve", 6, _BANCO)
    assert cubre is True
    # Los de su grado van primero y ordenados por nivel.
    assert ruta[:2] == ["NUEVO_6to_b", "NUEVO_6to_a"]
    assert "OTRO_PERFIL" not in ruta, "no debe cruzar perfiles"
    assert "COMP6_x" not in ruta, "la vía universal no entra a rutas diagnósticas"


def test_se_completa_con_la_ruta_curada_si_falta():
    # Solo hay 2 ejercicios de 6º; el presupuesto de 'leve' es 5.
    ruta, _ = build_route("fonologico", "leve", 6, _BANCO)
    assert len(ruta) == ROUTE_BUDGET["leve"]
    assert "CF_silabas_N1" in ruta, "se rellena con la ruta curada"


def test_grado_sin_nada_en_el_banco_conserva_la_ruta_completa():
    """Filtrar dejaría al alumno sin intervención, que es peor que darle
    material de otro grado. El flag avisa en vez de fingir que corresponde."""
    banco_sin_5to = {k: v for k, v in _BANCO.items() if "6" not in v["grados"]}
    ruta, cubre = build_route("fonologico", "leve", 5, banco_sin_5to)
    assert cubre is False
    assert ruta == get_route("fonologico", "leve"), "se entrega la ruta curada entera"
    assert ruta, "nunca vacía"


def test_el_presupuesto_depende_de_la_severidad_no_del_grado():
    for sev in ("leve", "moderado", "severo"):
        ruta, _ = build_route("fonologico", sev, 6, _BANCO)
        assert len(ruta) <= ROUTE_BUDGET[sev]


def test_sin_grado_se_comporta_como_antes():
    ruta, cubre = build_route("fonologico", "leve", None, _BANCO)
    assert cubre is True
    assert ruta == get_route("fonologico", "leve")


def test_la_ruta_es_estable_entre_llamadas():
    # Si el orden cambiara entre llamadas, el alumno vería la ruta barajarse.
    a, _ = build_route("fonologico", "leve", 6, _BANCO)
    b, _ = build_route("fonologico", "leve", 6, _BANCO)
    assert a == b


def test_si_la_curaduria_cubre_el_grado_no_se_toca():
    """La ruta curada codifica un orden clínico. Un primer intento de esta
    función anteponía los ejercicios del banco que calzaban por grado, y eso
    reemplazaba la curaduría entera en 24 de 36 combinaciones de 1º-3º —
    incluido un caso donde los 5 ejercicios curados salían y entraban otros 5.
    Solo se completa desde el banco cuando la curaduría no tiene NADA del grado.
    """
    banco = dict(_BANCO)
    # Un ejercicio de la ruta curada ahora sirve también a 6º...
    banco["CF_rima_N1"] = {"grados": ["1", "2", "6"],
                           "perfil_objetivo": ["fonologico"], "nivel": 1}

    ruta, cubre = build_route("fonologico", "leve", 6, banco)

    assert cubre is True
    assert ruta[0] == "CF_rima_N1", "el de su grado se adelanta"
    # ...y como la curaduría ya cubre 6º, los del banco NO se agregan.
    assert "NUEVO_6to_a" not in ruta
    assert "NUEVO_6to_b" not in ruta
    assert set(ruta) == set(get_route("fonologico", "leve")), \
        "la ruta sigue siendo la curada, solo reordenada"
