from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.dependencies.services import get_email_service
from api.v1.institutions.schemas import InstitutionResponse, RegisterInstitutionRequest
from config.settings import get_settings
from domain.ports.email_port import EmailPort
from infrastructure.database.repositories.pg_institution_repository import PgInstitutionRepository
from infrastructure.security.password_hasher import Argon2PasswordHasher
from infrastructure.security.user_repository import UserRepository
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.post("/register", status_code=201)
async def register_institution(
    payload: RegisterInstitutionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_service: EmailPort = Depends(get_email_service),
):
    """Autorregistro público de una institución nueva. Queda inactiva hasta
    que un SUPERADMIN la apruebe — el ADMIN fundador no puede loguear hasta
    entonces (ver bloqueo en /auth/login)."""
    user_repo = UserRepository(db)
    if await user_repo.get_by_email(payload.admin_email):
        raise HTTPException(status_code=409, detail="Email already registered")

    school = await PgInstitutionRepository(db).register(
        name=payload.school_name, cct=payload.cct, state=payload.state, municipality=payload.municipality
    )
    password_hash = Argon2PasswordHasher().hash(payload.admin_password)
    admin_user = await user_repo.create_user(
        email=payload.admin_email, password_hash=password_hash, role="ADMIN", institution_id=school["id"]
    )
    await AuditLogger().log(
        db,
        action=AuditEvent.INSTITUTION_REGISTERED.value,
        actor_id=admin_user["id"],
        actor_role="ADMIN",
        target_table="academic.schools",
        target_id=school["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"school_name": payload.school_name},
    )

    settings = get_settings()
    if settings.notification_email_to:
        background_tasks.add_task(
            email_service.send,
            to=settings.notification_email_to,
            subject=f"Nueva institución solicitada: {payload.school_name}",
            body=(
                f"Escuela: {payload.school_name}\n"
                f"CCT: {payload.cct or '—'}\n"
                f"Estado/Municipio: {payload.state}, {payload.municipality or '—'}\n"
                f"Admin fundador: {payload.admin_email}\n\n"
                "Entra a la app con tu cuenta SUPERADMIN para aprobarla."
            ),
        )

    return {"status": "pending_approval", "institution_id": str(school["id"])}


@router.get("/pending", response_model=list[InstitutionResponse])
async def list_pending_institutions(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("SUPERADMIN")),
):
    return await PgInstitutionRepository(db).list_pending()


@router.post("/{institution_id}/approve", response_model=InstitutionResponse)
@audited(AuditEvent.INSTITUTION_APPROVED, target_table="academic.schools", target_id_arg="institution_id")
async def approve_institution(
    institution_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("SUPERADMIN")),
):
    approved = await PgInstitutionRepository(db).approve(institution_id, approved_by=user.id)
    if not approved:
        raise HTTPException(status_code=404, detail="Institution not found")
    return approved
