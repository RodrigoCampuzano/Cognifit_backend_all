from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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

    # Acuse de recibo a quien solicitó. Antes solo se avisaba al SUPERADMIN:
    # el docente que registraba su escuela quedaba sin saber si la solicitud
    # llegó, y sin poder entrar hasta la aprobación no tenía forma de
    # comprobarlo dentro de la app.
    background_tasks.add_task(
        email_service.send,
        to=payload.admin_email,
        subject=f"Recibimos la solicitud de {payload.school_name}",
        body=(
            f"Hola,\n\n"
            f"Registramos la solicitud de {payload.school_name}. "
            "Queda pendiente de aprobación.\n\n"
            "Mientras tanto no vas a poder iniciar sesión: la cuenta se activa "
            "cuando se apruebe la escuela. Te avisamos por este mismo correo "
            "en cuanto suceda.\n\n"
            f"Datos registrados:\n"
            f"  Escuela: {payload.school_name}\n"
            f"  CCT: {payload.cct or '—'}\n"
            f"  Estado/Municipio: {payload.state}, {payload.municipality or '—'}\n"
            f"  Correo de administrador: {payload.admin_email}\n\n"
            "Si algún dato es incorrecto, respondé este correo antes de la "
            "aprobación.\n\n"
            "CogniFit Escolar"
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("SUPERADMIN")),
    email_service: EmailPort = Depends(get_email_service),
):
    repo = PgInstitutionRepository(db)
    approved = await repo.approve(institution_id, approved_by=user.id)
    if not approved:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Se avisa a quien hizo la solicitud. Sin esto la aprobación era invisible:
    # el ADMIN no podía entrar antes y nadie le decía cuándo ya podía, así que
    # el único camino era reintentar el login cada tanto.
    destinatario = await repo.admin_email(institution_id)
    if destinatario:
        background_tasks.add_task(
            email_service.send,
            to=destinatario,
            subject=f"{approved['name']} ya está aprobada",
            body=(
                f"Hola,\n\n"
                f"La escuela {approved['name']} fue aprobada. Ya podés iniciar "
                "sesión en CogniFit Escolar con el correo y la contraseña que "
                "registraste.\n\n"
                "Como administrador podés dar de alta docentes, crear grupos y "
                "asignar el tamizaje.\n\n"
                "CogniFit Escolar"
            ),
        )
    else:
        # Que no haya ADMIN es una inconsistencia: el registro siempre crea
        # uno. Se deja constancia en el log en vez de fallar la aprobación,
        # que ya se hizo y es lo que importa.
        logger.warning(
            "Institución %s aprobada pero sin ADMIN al cual avisar", institution_id
        )

    return approved
