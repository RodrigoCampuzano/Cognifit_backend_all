from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


class GenerateReportUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def request_report(self, *, requested_by: UUID, student_id: UUID, report_type: str) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO reporting.report_requests (requested_by, student_id, report_type, status)
                VALUES (:requested_by, :student_id, :report_type, 'PENDING')
                RETURNING id, requested_by, student_id, report_type, status, requested_at
                '''
            ),
            {"requested_by": str(requested_by), "student_id": str(student_id), "report_type": report_type},
        )
        return dict(result.mappings().one())

    async def build_payload(self, student_id: UUID) -> dict:
        student = await self.session.execute(
            text(
                '''
                SELECT s.id, pgp_sym_decrypt(s.full_name, :key)::text AS full_name, s.birth_year,
                       g.grade, g.group_label AS group_name
                FROM academic.students s JOIN academic.groups g ON g.id = s.group_id
                WHERE s.id = :sid
                '''
            ),
            {"sid": str(student_id), "key": self.settings.db_encryption_key},
        )
        risk = await self.session.execute(
            text("SELECT * FROM diagnosis.v_latest_student_risk WHERE student_id=:sid"),
            {"sid": str(student_id)},
        )
        route = await self.session.execute(
            text(
                '''
                SELECT exercise_route, total_exercises, pln_profile, assigned_at
                FROM intervention.student_paths WHERE student_id = :sid AND is_active
                ORDER BY assigned_at DESC LIMIT 1
                '''
            ),
            {"sid": str(student_id)},
        )
        return {
            "student_id": str(student_id),
            "student": dict(student.mappings().first() or {}),
            "latest_risk": dict(risk.mappings().first() or {}),
            "active_route": dict(route.mappings().first() or {}),
        }

    async def generate_pdf(self, report_id: UUID) -> dict:
        """Renderiza el PDF con ReportLab, lo guarda y marca el reporte READY (HU-BK-10)."""
        req = await self.session.execute(
            text("SELECT id, student_id, report_type, status FROM reporting.report_requests WHERE id = :rid"),
            {"rid": str(report_id)},
        )
        report = req.mappings().first()
        if not report:
            raise ValueError("Report request not found")

        payload = await self.build_payload(report["student_id"])
        reports_dir = Path(self.settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_path = reports_dir / f"{report_id}.pdf"

        self._render_pdf(file_path, report_type=report["report_type"], payload=payload)

        result = await self.session.execute(
            text(
                '''
                UPDATE reporting.report_requests
                SET status = 'READY', file_url = :file_url, completed_at = :completed_at
                WHERE id = :rid
                RETURNING id, student_id, report_type, status, file_url, completed_at
                '''
            ),
            {"rid": str(report_id), "file_url": str(file_path), "completed_at": datetime.now(timezone.utc)},
        )
        return dict(result.mappings().one())

    async def get_file(self, report_id: UUID) -> dict | None:
        result = await self.session.execute(
            text("SELECT id, student_id, status, file_url FROM reporting.report_requests WHERE id = :rid"),
            {"rid": str(report_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    def _render_pdf(self, file_path: Path, *, report_type: str, payload: dict) -> None:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        styles = getSampleStyleSheet()
        story = []
        student = payload.get("student", {})
        risk = payload.get("latest_risk", {})
        route = payload.get("active_route", {})

        titles = {
            "PARENT_SUMMARY": "Resumen para Padres/Tutores",
            "SPECIALIST_FULL": "Informe Completo para Especialista",
            "GROUP_OVERVIEW": "Resumen de Grupo",
        }
        story.append(Paragraph("CogniFit Escolar", styles["Title"]))
        story.append(Paragraph(titles.get(report_type, report_type), styles["Heading2"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            "Este documento entrega una estimación de riesgo y una ruta educativa adaptativa. "
            "No constituye un diagnóstico clínico.", styles["Italic"]))
        story.append(Spacer(1, 16))

        info = [
            ["Alumno", student.get("full_name", "—")],
            ["Grado", str(student.get("grade", "—"))],
            ["Grupo", student.get("group_name", "—")],
            ["Subtipo detectado", str(risk.get("subtype", "—"))],
            ["Severidad", str(risk.get("severity", "—"))],
            ["Nivel de riesgo", str(risk.get("risk_level", "—"))],
            ["Probabilidad de riesgo", str(risk.get("risk_probability", "—"))],
            ["Errores predominantes", ", ".join(risk.get("main_error_codes") or []) or "—"],
            ["Ejercicios en la ruta", str(route.get("total_exercises", 0))],
            ["Perfil de la ruta", str(route.get("pln_profile", "—"))],
        ]
        table = Table(info, colWidths=[170, 320])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 16))

        exercises = route.get("exercise_route") or []
        if exercises:
            story.append(Paragraph("Ruta de ejercicios asignada", styles["Heading3"]))
            for i, ex in enumerate(exercises, 1):
                story.append(Paragraph(f"{i}. {ex}", styles["Normal"]))
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"]))

        SimpleDocTemplate(str(file_path), pagesize=A4).build(story)
