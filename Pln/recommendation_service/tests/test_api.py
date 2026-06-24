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
