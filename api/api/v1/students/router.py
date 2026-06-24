from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.v1.students.schemas import RegisterStudentRequest, StudentResponse
from infrastructure.database.repositories.pg_student_repository import PgStudentRepository
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentResponse])
async def list_students(
    group_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await PgStudentRepository(db).list_students(group_id)


@router.post("", response_model=StudentResponse, status_code=201)
async def register_student(
    payload: RegisterStudentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    student = await PgStudentRepository(db).register_student(payload.model_dump())
    await AuditLogger().log(
        db,
        action=AuditEvent.REGISTER_STUDENT.value,
        actor_id=user.id,
        actor_role=user.role,
        target_table="academic.students",
        target_id=student["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return student


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
