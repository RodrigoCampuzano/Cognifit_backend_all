"""
Tests del Diagnosis Service.
Ejecutar con:  pytest tests/ -v
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
        assert r.json()["status"] == "ok"
        assert r.json()["models_loaded"] is True


def test_model_info():
    with TestClient(app) as client:
        r = client.get("/model/info")
        assert r.status_code == 200
        data = r.json()
        assert "subtype" in data and "severity" in data
        assert data["subtype"]["metrics"]["f1_macro"] >= 0.80
        assert data["severity"]["metrics"]["f1_macro"] >= 0.75


def test_diagnose_fonologico():
    """Un alumno que falla pseudopalabras pero acierta palabras reales -> fonológico."""
    payload = {
        "student_id": 21, "grade": 2, "teacher_score": 72.0,
        "items": [
            {"target": "plime", "response": "pime", "module": "pseudopalabras", "response_time_ms": 6500},
            {"target": "dubre", "response": "dube", "module": "pseudopalabras", "response_time_ms": 7200},
            {"target": "tribo", "response": "tibo", "module": "pseudopalabras", "response_time_ms": 6800},
            {"target": "casa", "response": "casa", "module": "palabras_reales", "response_time_ms": 2100},
            {"target": "mesa", "response": "mesa", "module": "palabras_reales", "response_time_ms": 1900},
            {"target": "perro", "response": "pero", "module": "dictado", "response_time_ms": 3200},
        ],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
        assert r.status_code == 200
        res = r.json()
        assert res["subtype"] == "fonologico"
        assert res["risk_level"] in ("medio", "alto")
        assert len(res["feature_vector"]) == 28


def test_diagnose_visual():
    """Un alumno con muchas rotaciones b/d/p/q -> visual."""
    payload = {
        "student_id": 1, "grade": 3, "teacher_score": 60.0,
        "items": [
            {"target": "dado", "response": "bado", "module": "pseudopalabras", "response_time_ms": 3000},
            {"target": "pollo", "response": "qollo", "module": "pseudopalabras", "response_time_ms": 3200},
            {"target": "bota", "response": "dota", "module": "palabras_reales", "response_time_ms": 2800},
            {"target": "dedo", "response": "bebo", "module": "dictado", "response_time_ms": 3100},
        ],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
        assert r.status_code == 200
        assert r.json()["subtype"] == "visual"


def test_diagnose_sin_riesgo():
    """Un alumno que acierta casi todo y rápido -> sin_riesgo."""
    payload = {
        "student_id": 2, "grade": 4, "teacher_score": 15.0,
        "items": [
            {"target": "casa", "response": "casa", "module": "palabras_reales", "response_time_ms": 1800},
            {"target": "mesa", "response": "mesa", "module": "palabras_reales", "response_time_ms": 1700},
            {"target": "plime", "response": "plime", "module": "pseudopalabras", "response_time_ms": 2200},
            {"target": "libro", "response": "libro", "module": "dictado", "response_time_ms": 2000},
        ],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
        assert r.status_code == 200
        res = r.json()
        assert res["subtype"] == "sin_riesgo"
        assert res["risk_level"] == "bajo"


def test_diagnose_handles_timeout():
    """Ítems sin respuesta deben contarse como timeout."""
    payload = {
        "student_id": 4, "grade": 2, "teacher_score": 80.0,
        "items": [
            {"target": "plime", "response": "", "module": "pseudopalabras", "response_time_ms": 16000},
            {"target": "casa", "response": "casa", "module": "palabras_reales", "response_time_ms": 2000},
        ],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
        assert r.status_code == 200
        assert r.json()["items_timeout"] == 1


def test_diagnose_rejects_empty_items():
    """Una sesión sin ítems debe ser rechazada por validación."""
    payload = {"student_id": 1, "grade": 2, "teacher_score": 0.0, "items": []}
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
        assert r.status_code == 422  # validation error


# ─── Errores a nivel de palabra (INV/SEG/UNI) ────────────────────────────────
# Estos codigos existian en error_detector pero el pipeline nunca los llamaba,
# asi que sus dimensiones del feature vector quedaban siempre en 0. Se fijan
# aca porque alimentan diagnosis.training_labels y por lo tanto el
# reentrenamiento futuro: sin ellos el proximo modelo volveria a aprender que
# ningun nino invierte letras.

def test_detecta_inversion_de_letras():
    """Marcador clasico de dislexia: 'perro' -> 'prero'."""
    payload = {
        "student_id": 1, "grade": 3, "teacher_score": 60.0,
        "items": [{"target": "perro", "response": "prero",
                   "module": "dictado", "response_time_ms": 3000}],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
    assert r.status_code == 200
    assert r.json()["error_breakdown"].get("INV", 0) >= 1


def test_detecta_union_y_segmentacion_de_palabras():
    for target, response, code in [("el sol", "elsol", "UNI"), ("casa", "ca sa", "SEG")]:
        payload = {
            "student_id": 1, "grade": 3, "teacher_score": 60.0,
            "items": [{"target": target, "response": response,
                       "module": "dictado", "response_time_ms": 3000}],
        }
        with TestClient(app) as client:
            r = client.post("/diagnose", json=payload)
        assert r.status_code == 200
        assert r.json()["error_breakdown"].get(code, 0) >= 1, f"falta {code} en {target!r}->{response!r}"


def test_h_muda_no_cuenta_como_error_diagnostico():
    """'hola' -> 'ola' es ortografia normal en espanol MX, no dislexia.
    Antes inflaba OMI_rate, que si es una feature con peso en el modelo."""
    payload = {
        "student_id": 1, "grade": 3, "teacher_score": 60.0,
        "items": [{"target": "hola", "response": "ola",
                   "module": "dictado", "response_time_ms": 3000}],
    }
    with TestClient(app) as client:
        r = client.post("/diagnose", json=payload)
    assert r.status_code == 200
    assert r.json()["error_breakdown"].get("OMI", 0) == 0
