from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.v1.admin.schemas import ActivateModelRequest, CreateUserRequest, LinkStudentRequest, UpdateUserRequest
from infrastructure.database.repositories.pg_model_version_repository import PgModelVersionRepository
from infrastructure.database.repositories.pg_student_repository import PgStudentRepository
from infrastructure.security.password_hasher import Argon2PasswordHasher
from infrastructure.security.user_repository import UserRepository
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/admin", tags=["admin"])


# ─────────────────────────── HU-BK-03 · Gestión de cuentas ───────────────────────────
@router.get("/users")
async def list_users(
    role: str | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    return await UserRepository(db).list_users(role=role, include_inactive=include_inactive, institution_id=user.institution_id)


@router.post("/users", status_code=201)
@audited(
    AuditEvent.REGISTER_USER,
    target_table="auth.users",
    metadata_fn=lambda result, kw: {"role": kw["payload"].role},
)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    repo = UserRepository(db)
    if await repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    return await repo.create_user(
        email=payload.email,
        password_hash=Argon2PasswordHasher().hash(payload.password),
        role=payload.role,
        institution_id=user.institution_id,
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    updated = await UserRepository(db).update_user(
        user_id, role=payload.role, is_active=payload.is_active, institution_id=user.institution_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@router.delete("/users/{user_id}")
@audited(AuditEvent.USER_DEACTIVATED, target_table="auth.users", target_id_arg="user_id")
async def deactivate_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """Borrado lógico (nunca físico)."""
    deactivated = await UserRepository(db).deactivate_user(user_id, institution_id=user.institution_id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="User not found")
    return deactivated


@router.patch("/users/{user_id}/link-student")
async def link_student_to_parent(
    user_id: UUID,
    payload: LinkStudentRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """Vincula la cuenta de un padre/tutor al alumno indicado, ambos dentro de la institución del admin."""
    linked = await PgStudentRepository(db).link_parent_to_student(user_id, payload.student_id, institution_id=user.institution_id)
    if not linked:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return {"linked": True}


# ─────────────────────── HU-BK-13 · Versiones del modelo de ML ───────────────────────
@router.get("/model-versions")
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST")),
):
    return await PgModelVersionRepository(db).list_versions()


@router.post("/model-versions/activate")
@audited(
    AuditEvent.MODEL_VERSION_ACTIVATED,
    target_table="diagnosis.ml_model_versions",
    metadata_fn=lambda result, kw: {"version_tag": kw["payload"].version_tag},
)
async def activate_model_version(
    payload: ActivateModelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """Activa una versión como producción. La DB bloquea activar sin métricas validadas."""
    repo = PgModelVersionRepository(db)
    try:
        return await repo.activate(payload.version_tag)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=422,
            detail="No se puede promover: el modelo no cumple los umbrales mínimos de métricas validadas.",
        ) from exc
