from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from infrastructure.database.repositories.pg_tracking_repository import PgTrackingRepository
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/students/{student_id}/learning-curve")
async def learning_curve(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    result = await PgTrackingRepository(db).learning_curve(
        student_id, requester_id=user.id, is_privileged=user.role in ("ADMIN", "SPECIALIST"), institution_id=user.institution_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return result


@router.get("/students/{student_id}/metrics")
async def student_metrics(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    result = await PgTrackingRepository(db).student_metrics(
        student_id, requester_id=user.id, is_privileged=user.role in ("ADMIN", "SPECIALIST"), institution_id=user.institution_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return result


@router.get("/groups/{group_id}/metrics")
async def group_metrics(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    result = await PgTrackingRepository(db).group_metrics(
        group_id, requester_id=user.id, is_privileged=user.role in ("ADMIN", "SPECIALIST"), institution_id=user.institution_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return result


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
@audited(
    AuditEvent.ALERT_GENERATED,
    target_table="tracking.alerts",
    condition=lambda result: bool(result.get("alert")),
    target_id_fn=lambda result, kw: result["alert"]["id"],
    metadata_fn=lambda result, kw: {"action": result["action"]},
)
async def evaluate_progress(
    student_id: UUID,
    request: Request,
    window: int = 5,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    """Analiza la serie temporal del alumno y genera alerta de estancamiento/recalibración (HU-MD-09)."""
    return await PgTrackingRepository(db).evaluate_progress(
        student_id,
        requester_id=user.id,
        is_privileged=user.role in ("ADMIN", "SPECIALIST"),
        institution_id=user.institution_id,
        window=window,
    )
