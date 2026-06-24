"""
CogniFit Escolar — Recommendation Service
Asigna rutas de aprendizaje adaptativas a partir del diagnóstico.

Endpoints:
  GET  /health                     → estado del servicio
  POST /recommend                  → genera ruta a partir de diagnóstico
  POST /next-exercise              → decide el próximo ejercicio
  GET  /exercises/{exercise_id}    → detalle de un ejercicio
  GET  /routes                     → lista todas las rutas disponibles
"""
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.routes import get_route, get_next_exercise, LEARNING_ROUTES

# ─── Carga del banco de ejercicios ───────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EXERCISE_BANK: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _EXERCISE_BANK
    bank_path = DATA_DIR / "banco_ejercicios_intervencion.json"
    if bank_path.exists():
        raw = json.loads(bank_path.read_text(encoding="utf-8"))
        _EXERCISE_BANK = {
            ex["exercise_id"]: ex
            for ex in raw.get("ejercicios", [])
        }
        print(f"[Recommendation Service] {len(_EXERCISE_BANK)} ejercicios cargados")
    else:
        print("[Recommendation Service] ADVERTENCIA: banco de ejercicios no encontrado")
    yield
    print("[Recommendation Service] Cerrando servicio.")


app = FastAPI(
    title="CogniFit Recommendation Service",
    description="Genera rutas de aprendizaje adaptativas según el perfil de dislexia.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Esquemas Pydantic ────────────────────────────────────────────────────────
class DiagnosisInput(BaseModel):
    student_id: int = Field(..., description="ID del alumno")
    subtype: str = Field(..., description="Subtipo: fonologico|visual|mixto|fluidez|sin_riesgo")
    severity: str = Field(..., description="Severidad: leve|moderado|severo|ninguna")
    risk_probability: Optional[float] = Field(None, description="Probabilidad de riesgo (0-1)")
    grade: Optional[int] = Field(None, ge=1, le=6, description="Grado escolar")

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": 21,
                "subtype": "fonologico",
                "severity": "leve",
                "risk_probability": 0.994,
                "grade": 2,
            }
        }
    }


class ExerciseRef(BaseModel):
    exercise_id: str
    order: int
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    usa_tts: Optional[bool] = None
    usa_stt: Optional[bool] = None
    nivel: Optional[int] = None


class RouteResponse(BaseModel):
    student_id: int
    subtype: str
    severity: str
    total_exercises: int
    exercises: list[ExerciseRef]
    message: str


class SessionRecord(BaseModel):
    exercise_id: str
    accuracy: float = Field(..., ge=0, le=1)


class NextExerciseInput(BaseModel):
    student_id: int
    current_route: list[str] = Field(..., description="Lista de exercise_ids de la ruta activa")
    session_history: list[SessionRecord] = Field(
        default=[], description="Historial de sesiones: [{exercise_id, accuracy}]"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": 21,
                "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
                "session_history": [
                    {"exercise_id": "CF_silabas_N1", "accuracy": 0.95},
                    {"exercise_id": "CF_silabas_N1", "accuracy": 0.92},
                    {"exercise_id": "CF_silabas_N1", "accuracy": 0.91},
                ],
            }
        }
    }


class NextExerciseResponse(BaseModel):
    student_id: int
    exercise_id: Optional[str]
    action: str
    trigger: Optional[str] = None
    support: Optional[str] = None
    exercise_detail: Optional[dict] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def enrich_exercise(exercise_id: str, order: int) -> ExerciseRef:
    """Enriquece un exercise_id con datos del banco."""
    detail = _EXERCISE_BANK.get(exercise_id, {})
    return ExerciseRef(
        exercise_id=exercise_id,
        order=order,
        tipo=detail.get("tipo"),
        titulo=detail.get("titulo"),
        usa_tts=detail.get("usa_tts"),
        usa_stt=detail.get("usa_stt"),
        nivel=detail.get("nivel"),
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "recommendation",
        "exercises_loaded": len(_EXERCISE_BANK),
    }


@app.get("/routes")
async def list_routes():
    """Lista todas las rutas disponibles con su cantidad de ejercicios."""
    return {
        f"{subtype}/{severity}": {
            "exercises": ids,
            "total": len(ids),
        }
        for (subtype, severity), ids in LEARNING_ROUTES.items()
        if ids  # omitir sin_riesgo (ruta vacía)
    }


@app.post("/recommend", response_model=RouteResponse)
async def recommend(diagnosis: DiagnosisInput):
    """
    Genera la ruta de aprendizaje para un alumno dado su diagnóstico.
    El Test Service llama este endpoint justo después del Diagnosis Service.
    """
    subtype = diagnosis.subtype.lower().strip()
    severity = diagnosis.severity.lower().strip()

    # sin_riesgo no necesita intervención
    if subtype == "sin_riesgo":
        return RouteResponse(
            student_id=diagnosis.student_id,
            subtype=subtype,
            severity=severity,
            total_exercises=0,
            exercises=[],
            message="Sin riesgo detectado. Se activa monitoreo periódico sin intervención.",
        )

    route_ids = get_route(subtype, severity)

    if not route_ids:
        raise HTTPException(
            status_code=404,
            detail=f"No hay ruta definida para ({subtype}, {severity}). "
                   f"Subtipos válidos: fonologico, visual, mixto, fluidez, sin_riesgo. "
                   f"Severidades válidas: leve, moderado, severo.",
        )

    exercises = [enrich_exercise(eid, i + 1) for i, eid in enumerate(route_ids)]

    return RouteResponse(
        student_id=diagnosis.student_id,
        subtype=subtype,
        severity=severity,
        total_exercises=len(exercises),
        exercises=exercises,
        message=f"Ruta adaptativa generada: {len(exercises)} ejercicios "
                f"para perfil {subtype}/{severity}.",
    )


@app.post("/next-exercise", response_model=NextExerciseResponse)
async def next_exercise(data: NextExerciseInput):
    """
    Decide el próximo ejercicio basado en el desempeño reciente del alumno.
    El Exercise Service llama este endpoint después de cada sesión completada.
    """
    history = [s.model_dump() for s in data.session_history]
    decision = get_next_exercise(data.current_route, history)

    exercise_detail = None
    if decision.get("exercise_id"):
        exercise_detail = _EXERCISE_BANK.get(decision["exercise_id"])

    return NextExerciseResponse(
        student_id=data.student_id,
        exercise_id=decision.get("exercise_id"),
        action=decision["action"],
        trigger=decision.get("trigger"),
        support=decision.get("support"),
        exercise_detail=exercise_detail,
    )


@app.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    """Detalle completo de un ejercicio del banco."""
    exercise = _EXERCISE_BANK.get(exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404,
            detail=f"Ejercicio '{exercise_id}' no encontrado en el banco.",
        )
    return exercise
