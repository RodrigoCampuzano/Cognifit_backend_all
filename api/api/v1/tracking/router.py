from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from infrastructure.database.repositories.pg_tracking_repository import PgTrackingRepository
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/students/{student_id}/learning-curve")
async def learning_curve(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    return await PgTrackingRepository(db).learning_curve(student_id)


@router.get("/students/{student_id}/metrics")
async def student_metrics(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    return await PgTrackingRepository(db).student_metrics(student_id)


@router.get("/groups/{group_id}/metrics")
async def group_metrics(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await PgTrackingRepository(db).group_metrics(group_id)


@router.get("/alerts")
async def list_alerts(
    only_unread: bool = False,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await PgTrackingRepository(db).list_alerts(user.id, only_unread=only_unread)


@router.post("/alerts/{alert_id}/read", status_code=200)
async def mark_alert_read(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    updated = await PgTrackingRepository(db).mark_alert_read(alert_id, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
    return updated


@router.post("/students/{student_id}/evaluate-progress")
async def evaluate_progress(
    student_id: UUID,
    request: Request,
    window: int = 5,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    """Analiza la serie temporal del alumno y genera alerta de estancamiento/recalibración (HU-MD-09)."""
    result = await PgTrackingRepository(db).evaluate_progress(student_id, window=window)
    if result.get("alert"):
        await AuditLogger().log(
            db,
            action=AuditEvent.ALERT_GENERATED.value,
            actor_id=user.id,
            actor_role=user.role,
            target_table="tracking.alerts",
            target_id=result["alert"]["id"],
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"action": result["action"]},
        )
    return result
