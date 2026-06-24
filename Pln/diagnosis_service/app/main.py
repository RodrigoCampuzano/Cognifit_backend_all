"""
CogniFit Escolar — Diagnosis Service
API FastAPI que expone el pipeline PLN + ML como microservicio REST.

Endpoints:
  GET  /health           -> estado del servicio (para el monitoreo del admin)
  GET  /model/info       -> versión y métricas de los modelos cargados
  POST /diagnose         -> diagnóstico de una sesión completa
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.ml.predictor import ModelRegistry
from app.pipeline import process_session

# ─── Estado global: modelos cargados una sola vez al arrancar ────────────────
registry: Optional[ModelRegistry] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga los modelos al arrancar y los mantiene en memoria."""
    global registry
    registry = ModelRegistry()
    print(f"[Diagnosis Service] Modelos cargados: {registry.info['subtype']['version']}")
    yield
    print("[Diagnosis Service] Cerrando servicio.")


app = FastAPI(
    title="CogniFit Diagnosis Service",
    description="Pipeline PLN + ML para detección de riesgo de dislexia.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Esquemas Pydantic ───────────────────────────────────────────────────────
class TestItem(BaseModel):
    target: str = Field(..., description="Texto/palabra esperada")
    response: str = Field("", description="Texto producido por el alumno (vacío si timeout)")
    module: str = Field(..., description="Módulo del test: pseudopalabras, palabras_reales, dictado, etc.")
    response_time_ms: int = Field(0, ge=0, description="Tiempo de respuesta en ms")
    difficulty_level: Optional[int] = Field(1, description="Nivel de dificultad del ítem")
    input_method: Optional[str] = Field("stt", description="stt | teclado | tactil")


class SessionData(BaseModel):
    student_id: int = Field(..., description="ID del alumno")
    grade: int = Field(..., ge=1, le=6, description="Grado escolar (1-6)")
    teacher_score: float = Field(0.0, ge=0, le=100, description="Score del cuestionario PRODISLEX (0-100)")
    session_number: Optional[int] = Field(1, description="Número de sesión del alumno")
    items: list[TestItem] = Field(..., min_length=1, description="Ítems del test")

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": 21,
                "grade": 2,
                "teacher_score": 72.0,
                "session_number": 1,
                "items": [
                    {"target": "plime", "response": "pime", "module": "pseudopalabras",
                     "response_time_ms": 6500, "difficulty_level": 2, "input_method": "stt"},
                    {"target": "casa", "response": "casa", "module": "palabras_reales",
                     "response_time_ms": 2100, "difficulty_level": 1, "input_method": "stt"},
                ],
            }
        }
    }


class DiagnosisResult(BaseModel):
    subtype: str
    subtype_confidence: float
    severity: str
    severity_confidence: float
    risk_probability: float
    risk_level: str
    model_version: Optional[str]
    main_error_codes: list[str]
    error_breakdown: dict
    items_processed: int
    items_timeout: int
    feature_vector: list[float]


# ─── Endpoints ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Estado del servicio. Lo consulta el panel admin para el monitoreo."""
    return {
        "status": "ok" if registry is not None else "loading",
        "service": "diagnosis",
        "models_loaded": registry is not None,
    }


@app.get("/model/info")
async def model_info():
    """Versión y métricas de los modelos activos (gestión de versiones del admin)."""
    if registry is None:
        raise HTTPException(status_code=503, detail="Modelos no cargados aún")
    return registry.info


@app.post("/diagnose", response_model=DiagnosisResult)
async def diagnose(session: SessionData):
    """
    Recibe una sesión de test completa y devuelve el diagnóstico probabilístico.
    Este es el endpoint que llama el Test Service tras cerrar un test.
    """
    if registry is None:
        raise HTTPException(status_code=503, detail="Modelos no cargados aún")
    try:
        session_dict = session.model_dump()
        result = process_session(session_dict, registry)
        return DiagnosisResult(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el pipeline: {e}")
