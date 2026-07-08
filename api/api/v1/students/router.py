from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.v1.students.schemas import LinkedStudentResponse, RegisterStudentRequest, StudentResponse
from infrastructure.database.repositories.pg_student_repository import PgStudentRepository
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/linked", response_model=LinkedStudentResponse)
async def get_linked_student(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("STUDENT", "PARENT")),
):
    """Devuelve el alumno vinculado al usuario autenticado (alumno propio o hijo del padre)."""
    student = await PgStudentRepository(db).get_linked_student(user.id)
    if not student:
        raise HTTPException(status_code=404, detail="No se encontró alumno vinculado a este usuario")
    return student


@router.get("", response_model=list[StudentResponse])
async def list_students(
    group_id: UUID | None = None,
    grade: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await PgStudentRepository(db).list_students(
        user.id,
        is_privileged=user.role in ("ADMIN", "SPECIALIST"),
        group_id=group_id,
        grade=grade,
    )


@router.post("", response_model=StudentResponse, status_code=201)
@audited(AuditEvent.REGISTER_STUDENT, target_table="academic.students")
async def register_student(
    payload: RegisterStudentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    return await PgStudentRepository(db).register_student(payload.model_dump())


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    student = await PgStudentRepository(db).get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/{student_id}", status_code=204)
@audited(AuditEvent.DELETE_STUDENT, target_table="academic.students", target_id_arg="student_id")
async def delete_student(
    student_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    deleted = await PgStudentRepository(db).deactivate_student(student_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Student not found")


@router.delete("/{student_id}/permanent", status_code=204)
@audited(AuditEvent.PERMANENT_DELETE_STUDENT, target_table="academic.students", target_id_arg="student_id")
async def permanent_delete_student(
    student_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """Borrado físico irreversible — solo ADMIN. Elimina todos los datos del alumno."""
    deleted = await PgStudentRepository(db).permanent_delete_student(student_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Student not found")


@router.patch("/{student_id}/activate", response_model=StudentResponse)
@audited(AuditEvent.ACTIVATE_STUDENT, target_table="academic.students", target_id_arg="student_id")
async def activate_student(
    student_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    activated = await PgStudentRepository(db).activate_student(student_id)
    if not activated:
        raise HTTPException(status_code=404, detail="Student not found or already active")
    return await PgStudentRepository(db).get_student(student_id)
