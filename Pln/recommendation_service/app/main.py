"""
CogniFit Escolar — Recommendation Service
Asigna rutas de aprendizaje adaptativas a partir del diagnóstico.

Endpoints:
  GET  /health                     → estado del servicio
  POST /recommend                  → genera ruta a partir de diagnóstico
  POST /next-exercise              → decide el próximo ejercicio
  GET  /exercises/{exercise_id}    → detalle de un ejercicio
  GET  /comprehension/{grade}      → comprensión por grado (vía universal)
  GET  /routes                     → lista todas las rutas disponibles

Hay dos vías de entrega y no se mezclan:
  · intervención → por perfil diagnóstico (subtipo, severidad)
  · comprensión  → por grado, sin pasar por el diagnóstico
"""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.routes import get_route, get_next_exercise, build_route, LEARNING_ROUTES

logger = logging.getLogger(__name__)

# ─── Carga del banco de ejercicios ───────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Banco de intervención: se entrega por perfil diagnóstico (LEARNING_ROUTES).
_EXERCISE_BANK: dict[str, dict] = {}

# Banco de comprensión: se entrega por GRADO, no por perfil. Va aparte porque el
# criterio de entrega es distinto — el tamizaje mide nivel palabra y no puede
# detectar dificultades de comprensión, así que estos ejercicios no cuelgan de
# ningún subtipo. Mezclarlos en LEARNING_ROUTES los volvería inalcanzables (es
# lo que le pasó a M10_VD) o los entregaría por un perfil que no los predice.
_COMPREHENSION_BY_GRADE: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _EXERCISE_BANK, _COMPREHENSION_BY_GRADE

    # Se reinician en cada arranque: el índice por grado se construye con
    # append, así que un segundo lifespan sobre el mismo proceso (recarga en
    # desarrollo, varios TestClient) duplicaría los ejercicios en silencio.
    _EXERCISE_BANK = {}
    _COMPREHENSION_BY_GRADE = {}

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

    comp_path = DATA_DIR / "banco_comprension_universal.json"
    if comp_path.exists():
        raw = json.loads(comp_path.read_text(encoding="utf-8"))
        for ex in raw.get("ejercicios", []):
            eid = ex["exercise_id"]
            # Una colisión de id haría que /exercises/{id} devolviera el
            # ejercicio equivocado sin avisar. Se detiene el arranque.
            if eid in _EXERCISE_BANK:
                raise RuntimeError(
                    f"exercise_id duplicado entre bancos: {eid!r}. "
                    "Los ids deben ser únicos entre el banco de intervención "
                    "y el de comprensión."
                )
            _EXERCISE_BANK[eid] = ex
            for grado in ex.get("grados", []):
                _COMPREHENSION_BY_GRADE.setdefault(str(grado), []).append(ex)

        cobertura = {g: len(v) for g, v in sorted(_COMPREHENSION_BY_GRADE.items())}
        print(f"[Recommendation Service] comprensión por grado: {cobertura}")
        if not raw.get("revisado_por_especialista", False):
            print(
                "[Recommendation Service] AVISO: el banco de comprensión está "
                "marcado como NO revisado por especialista."
            )
    else:
        print("[Recommendation Service] ADVERTENCIA: banco de comprensión no encontrado")

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
    grade_appropriate: bool = True   # False si el banco no cubre el grado del alumno
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

    # La ruta se arma con el grado, no solo con (subtipo, severidad): antes un
    # alumno de 6º recibía ejercicios etiquetados para 1º-2º sin ninguna señal.
    route_ids, grade_appropriate = build_route(
        subtype, severity, diagnosis.grade, _EXERCISE_BANK
    )

    exercises = [enrich_exercise(eid, i + 1) for i, eid in enumerate(route_ids)]

    message = (
        f"Ruta adaptativa generada: {len(exercises)} ejercicios "
        f"para perfil {subtype}/{severity}."
    )
    if not grade_appropriate:
        logger.warning(
            "Ruta %s/%s para grado %s: el banco no tiene ejercicios de ese grado; "
            "se entrega la ruta completa igualmente.",
            subtype, severity, diagnosis.grade,
        )
        message += (
            f" Aviso: el banco no cubre el grado {diagnosis.grade}; "
            "los ejercicios pueden ser de un grado distinto."
        )

    return RouteResponse(
        student_id=diagnosis.student_id,
        subtype=subtype,
        severity=severity,
        total_exercises=len(exercises),
        exercises=exercises,
        grade_appropriate=grade_appropriate,
        message=message,
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


@app.get("/comprehension/{grade}")
async def comprehension_track(grade: str):
    """Ejercicios de comprensión para un grado — vía universal.

    No recibe subtipo ni severidad a propósito: esta vía no depende del
    diagnóstico. Cualquier alumno del grado puede recibirlos, tenga o no un
    perfil de riesgo.

    Devuelve 200 con lista vacía cuando el grado aún no tiene contenido, en vez
    de 404: para el cliente "todavía no hay material para 3º" es una respuesta
    válida, no un error, y un 404 lo obligaría a distinguir eso de un grado que
    no existe.
    """
    ejercicios = _COMPREHENSION_BY_GRADE.get(str(grade), [])
    return {
        "grade": str(grade),
        "via": "universal_grado",
        "total": len(ejercicios),
        "exercises": [
            {
                "exercise_id": ex["exercise_id"],
                "titulo": ex["titulo"],
                "subtipo": ex["subtipo"],
                "instruccion": ex["instruccion"],
                "modalidad": ex["modalidad"],
                "total_preguntas": len(ex.get("items", [])),
            }
            for ex in ejercicios
        ],
        # Los grados con contenido, para que la UI no ofrezca una vía vacía.
        "grados_con_contenido": sorted(_COMPREHENSION_BY_GRADE),
    }


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
