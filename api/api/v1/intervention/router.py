from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.dependencies.services import get_recommendation_client
from api.v1.intervention.schemas import NextExerciseRequest
from infrastructure.pln.errors import PlnServiceError
from infrastructure.pln.recommendation_client import RecommendationServiceClient

router = APIRouter(prefix="/intervention", tags=["intervention"])


@router.get("/students/{student_id}/active-path")
async def active_path(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT", "PARENT")),
):
    """Ruta de intervención activa del alumno (persistida tras el diagnóstico)."""
    result = await db.execute(
        text(
            '''
            SELECT sp.id, sp.exercise_route, sp.total_exercises, sp.pln_profile,
                   sp.current_difficulty, sp.route_reason, sp.assigned_at, rt.route_code
            FROM intervention.student_paths sp
            LEFT JOIN intervention.route_templates rt ON rt.id = sp.route_template_id
            WHERE sp.student_id = :student_id AND sp.is_active
            ORDER BY sp.assigned_at DESC
            LIMIT 1
            '''
        ),
        {"student_id": str(student_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No active learning path for student")
    return dict(row)


@router.post("/students/{student_id}/next-exercise")
async def next_exercise(
    student_id: UUID,
    payload: NextExerciseRequest,
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
    client: RecommendationServiceClient = Depends(get_recommendation_client),
):
    """Decide el próximo ejercicio (proxy al Recommendation Service, 8002)."""
    try:
        return await client.next_exercise(
            {
                "student_id": int(UUID(str(student_id)).hex[:8], 16),
                "current_route": payload.current_route,
                "session_history": [r.model_dump() for r in payload.session_history],
            }
        )
    except PlnServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Recommendation Service: {exc.detail}") from exc


@router.get("/exercises/{exercise_id}")
async def get_exercise(
    exercise_id: str,
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
    client: RecommendationServiceClient = Depends(get_recommendation_client),
):
    """Contenido completo de un ejercicio (proxy al Recommendation Service, 8002)."""
    try:
        return await client.get_exercise(exercise_id)
    except PlnServiceError as exc:
        status = exc.status_code if exc.status_code in (404,) else 503
        raise HTTPException(status_code=status, detail=f"Recommendation Service: {exc.detail}") from exc
