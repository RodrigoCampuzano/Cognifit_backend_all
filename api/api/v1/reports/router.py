from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from application.use_cases.reports.generate_report import GenerateReportUseCase
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    student_id: UUID
    report_type: str = Field(pattern="^(PARENT_SUMMARY|SPECIALIST_FULL|GROUP_OVERVIEW)$")


@router.post("", status_code=202)
async def request_report(
    payload: ReportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    report = await GenerateReportUseCase(db).request_report(requested_by=user.id, student_id=payload.student_id, report_type=payload.report_type)
    await AuditLogger().log(
        db,
        action=AuditEvent.REPORT_REQUESTED.value,
        actor_id=user.id,
        actor_role=user.role,
        target_table="reporting.report_requests",
        target_id=report["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return report


@router.get("/students/{student_id}/payload")
async def report_payload(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await GenerateReportUseCase(db).build_payload(student_id)


@router.post("/{report_id}/generate")
async def generate_report_pdf(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    """Renderiza el PDF con ReportLab y deja el reporte en estado READY (HU-BK-10)."""
    try:
        result = await GenerateReportUseCase(db).generate_pdf(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditLogger().log(
        db,
        action=AuditEvent.REPORT_GENERATED.value,
        actor_id=user.id,
        actor_role=user.role,
        target_table="reporting.report_requests",
        target_id=report_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return result


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    report = await GenerateReportUseCase(db).get_file(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    file_url = report.get("file_url")
    if report.get("status") != "READY" or not file_url or not os.path.exists(file_url):
        raise HTTPException(status_code=409, detail="Report not generated yet. Call POST /{id}/generate first.")
    return FileResponse(file_url, media_type="application/pdf", filename=f"reporte_{report_id}.pdf")
