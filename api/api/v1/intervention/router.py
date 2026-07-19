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
from infrastructure.pln.mappings import pln_student_id
from infrastructure.pln.recommendation_client import RecommendationServiceClient

router = APIRouter(prefix="/intervention", tags=["intervention"])


async def _verify_student_ownership(db: AsyncSession, student_id: UUID, user: CurrentUser) -> bool:
    if user.role in ("ADMIN", "SPECIALIST"):
        clause = "g.school_id = :institution_id"
    else:
        clause = "g.school_id = :institution_id AND (g.teacher_id = :uid OR s.parent_user_id = :uid OR s.user_id = :uid)"
    result = await db.execute(
        text(
            f'''
            SELECT 1 FROM academic.students s
            JOIN academic.groups g ON g.id = s.group_id
            WHERE s.id = :sid AND {clause}
            '''
        ),
        {"sid": str(student_id), "institution_id": str(user.institution_id), "uid": str(user.id)},
    )
    return result.first() is not None


@router.get("/students/{student_id}/active-path")
async def active_path(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT", "PARENT")),
):
    """Ruta de intervención activa del alumno (persistida tras el diagnóstico)."""
    if not await _verify_student_ownership(db, student_id, user):
        raise HTTPException(status_code=404, detail="Student not found")
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


@router.get("/students/{student_id}/comprehension")
async def comprehension_track(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT", "PARENT")),
    client: RecommendationServiceClient = Depends(get_recommendation_client),
):
    """Ejercicios de comprensión del grado del alumno (vía universal).

    A diferencia de /active-path, esta vía NO depende del diagnóstico: el
    tamizaje mide a nivel palabra y no detecta dificultades de comprensión, así
    que estos ejercicios se ofrecen a cualquier alumno del grado.

    El grado se lee del alumno en el servidor y no se acepta del cliente: si
    viniera en la petición, cualquiera podría pedir el material de otro grado
    y, peor, serviría para sondear grados ajenos sin pasar por la verificación
    de propiedad.
    """
    if not await _verify_student_ownership(db, student_id, user):
        raise HTTPException(status_code=404, detail="Student not found")

    result = await db.execute(
        text(
            '''
            SELECT g.grade
            FROM academic.students s
            JOIN academic.groups g ON g.id = s.group_id
            WHERE s.id = :student_id
            '''
        ),
        {"student_id": str(student_id)},
    )
    row = result.first()
    if not row or row[0] is None:
        raise HTTPException(
            status_code=409,
            detail="El alumno no tiene grado asignado; la vía de comprensión se entrega por grado.",
        )

    try:
        return await client.comprehension_track(str(row[0]))
    except PlnServiceError as exc:
        raise HTTPException(
            status_code=503, detail=f"Recommendation Service: {exc.detail}"
        ) from exc


@router.post("/students/{student_id}/next-exercise")
async def next_exercise(
    student_id: UUID,
    payload: NextExerciseRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
    client: RecommendationServiceClient = Depends(get_recommendation_client),
):
    """Decide el próximo ejercicio (proxy al Recommendation Service, 8002)."""
    if not await _verify_student_ownership(db, student_id, user):
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        return await client.next_exercise(
            {
                "student_id": pln_student_id(student_id),
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
