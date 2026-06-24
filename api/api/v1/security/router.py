from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.v1.security.schemas import AuditEventRequest, TriggerWipeRequest
from application.use_cases.security.trigger_wipe import TriggerWipeUseCase
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/controls")
async def controls(_: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST"))):
    return {
        "password_hashing": "Argon2id via argon2-cffi",
        "tokens": "JWT access corto + refresh token hasheado y revocable",
        "headers": ["CSP", "HSTS on HTTPS", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"],
        "traffic": "Rate limit por IP/ruta; Redis listo para entorno distribuido",
        "db": ["RLS preparado", "PII con pgcrypto", "audit.audit_log append-only", "verificador de schema"],
        "owasp": ["API1 RBAC", "API2 auth fuerte", "API3 proteccion de datos", "API4 rate limit", "API7 config segura", "API8 inventario/versionado", "API10 logs"],
    }


@router.post("/audit", status_code=201)
async def write_audit_event(
    payload: AuditEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST")),
):
    await AuditLogger().log(
        db,
        action=payload.action,
        actor_id=user.id,
        actor_role=user.role,
        target_table=payload.target_table,
        target_id=payload.target_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata=payload.metadata,
    )
    return {"status": "logged"}


@router.post("/remote-wipe", status_code=202)
async def remote_wipe(
    payload: TriggerWipeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    result = await TriggerWipeUseCase().execute(payload.user_id, payload.device_id, payload.reason)
    await AuditLogger().log(
        db,
        action=AuditEvent.WIPE_TRIGGERED.value,
        actor_id=user.id,
        actor_role=user.role,
        target_table="auth.users",
        target_id=payload.user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"device_id": payload.device_id, "reason": payload.reason},
    )
    return result
