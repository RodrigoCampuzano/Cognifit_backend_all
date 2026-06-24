from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgTrackingRepository:
    """Seguimiento longitudinal: curva de aprendizaje, métricas y alertas (HU-BK-09 / HU-MD-07/09)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def learning_curve(self, student_id: UUID) -> dict:
        """Serie temporal por sesión diagnóstica + sesiones de ejercicio del alumno."""
        diag = await self.session.execute(
            text(
                '''
                SELECT session_number, session_date, accuracy, error_rate, avg_response_ms,
                       risk_probability, risk_level, subtype, severity
                FROM tracking.diagnosis_ml_sessions
                WHERE student_id = :sid
                ORDER BY session_date ASC
                '''
            ),
            {"sid": str(student_id)},
        )
        exercises = await self.session.execute(
            text(
                '''
                SELECT es.started_at, es.completed_at, es.score, es.accuracy_pct, es.avg_response_ms,
                       e.exercise_code, e.title
                FROM intervention.exercise_sessions es
                JOIN intervention.student_paths sp ON sp.id = es.student_path_id
                JOIN intervention.exercises e ON e.id = es.exercise_id
                WHERE sp.student_id = :sid
                ORDER BY es.started_at ASC
                '''
            ),
            {"sid": str(student_id)},
        )
        return {
            "student_id": str(student_id),
            "diagnostic_sessions": [dict(r) for r in diag.mappings().all()],
            "exercise_sessions": [dict(r) for r in exercises.mappings().all()],
        }

    async def student_metrics(self, student_id: UUID) -> dict:
        result = await self.session.execute(
            text(
                '''
                WITH ml AS (
                    SELECT accuracy, error_rate, risk_probability, risk_level, subtype, severity, session_date
                    FROM tracking.diagnosis_ml_sessions WHERE student_id = :sid ORDER BY session_date
                ),
                ex AS (
                    SELECT es.accuracy_pct, es.started_at
                    FROM intervention.exercise_sessions es
                    JOIN intervention.student_paths sp ON sp.id = es.student_path_id
                    WHERE sp.student_id = :sid AND es.accuracy_pct IS NOT NULL ORDER BY es.started_at
                )
                SELECT
                    (SELECT count(*) FROM ml) AS diagnostic_sessions,
                    (SELECT count(*) FROM ex) AS exercise_sessions,
                    (SELECT risk_level FROM ml ORDER BY session_date DESC LIMIT 1) AS latest_risk_level,
                    (SELECT subtype   FROM ml ORDER BY session_date DESC LIMIT 1) AS latest_subtype,
                    (SELECT severity  FROM ml ORDER BY session_date DESC LIMIT 1) AS latest_severity,
                    (SELECT avg(accuracy_pct) FROM (SELECT accuracy_pct FROM ex ORDER BY started_at DESC LIMIT 3) t) AS recent_avg_accuracy,
                    (SELECT accuracy_pct FROM ex ORDER BY started_at ASC  LIMIT 1) AS first_accuracy,
                    (SELECT accuracy_pct FROM ex ORDER BY started_at DESC LIMIT 1) AS last_accuracy
                '''
            ),
            {"sid": str(student_id)},
        )
        row = dict(result.mappings().one())
        first, last = row.get("first_accuracy"), row.get("last_accuracy")
        row["trend"] = "n/a"
        if first is not None and last is not None:
            row["trend"] = "improving" if last > first + 0.02 else ("regressing" if last < first - 0.02 else "flat")
        return row

    async def group_metrics(self, group_id: UUID) -> dict:
        result = await self.session.execute(
            text(
                '''
                SELECT
                    count(DISTINCT s.id) AS total_students,
                    count(DISTINCT d.student_id) FILTER (WHERE d.risk_level = 'HIGH')   AS high_risk,
                    count(DISTINCT d.student_id) FILTER (WHERE d.risk_level = 'MEDIUM') AS medium_risk,
                    count(DISTINCT d.student_id) FILTER (WHERE d.risk_level = 'LOW')    AS low_risk
                FROM academic.students s
                LEFT JOIN LATERAL (
                    SELECT risk_level, student_id FROM diagnosis.diagnoses
                    WHERE student_id = s.id ORDER BY diagnosed_at DESC LIMIT 1
                ) d ON TRUE
                WHERE s.group_id = :gid AND s.is_active
                '''
            ),
            {"gid": str(group_id)},
        )
        return {"group_id": str(group_id), **dict(result.mappings().one())}

    async def list_alerts(self, teacher_id: UUID, *, only_unread: bool = False) -> list[dict]:
        clause = "AND is_read = FALSE" if only_unread else ""
        result = await self.session.execute(
            text(
                f'''
                SELECT id, student_id, alert_type, message, suggested_action, urgency,
                       is_read, created_at, read_at, source_session_id
                FROM tracking.alerts
                WHERE teacher_id = :tid {clause}
                ORDER BY created_at DESC
                '''
            ),
            {"tid": str(teacher_id)},
        )
        return [dict(r) for r in result.mappings().all()]

    async def mark_alert_read(self, alert_id: UUID, teacher_id: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                UPDATE tracking.alerts SET is_read = TRUE, read_at = now()
                WHERE id = :aid AND teacher_id = :tid
                RETURNING id, is_read, read_at
                '''
            ),
            {"aid": str(alert_id), "tid": str(teacher_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def evaluate_progress(self, student_id: UUID, *, window: int = 5, level_up_window: int = 3) -> dict:
        """Analiza las últimas sesiones de ejercicio: detecta estancamiento (sin mejora en
        `window` sesiones) o recalibración (>90% en `level_up_window`). Crea alerta deduplicada."""
        teacher = await self.session.execute(
            text(
                '''
                SELECT g.teacher_id FROM academic.students s
                JOIN academic.groups g ON g.id = s.group_id WHERE s.id = :sid
                '''
            ),
            {"sid": str(student_id)},
        )
        teacher_id = teacher.scalar_one_or_none()
        if not teacher_id:
            return {"student_id": str(student_id), "evaluated": False, "reason": "student/teacher not found"}

        rows = await self.session.execute(
            text(
                '''
                SELECT es.accuracy_pct
                FROM intervention.exercise_sessions es
                JOIN intervention.student_paths sp ON sp.id = es.student_path_id
                WHERE sp.student_id = :sid AND es.accuracy_pct IS NOT NULL
                ORDER BY es.started_at DESC
                LIMIT :win
                '''
            ),
            {"sid": str(student_id), "win": window},
        )
        accs = [float(r[0]) for r in rows.all()]
        result: dict = {"student_id": str(student_id), "evaluated": True, "sessions_considered": len(accs), "action": "none", "alert": None}

        if len(accs) >= level_up_window and all(a >= 0.90 for a in accs[:level_up_window]):
            result["action"] = "level_up"
            result["alert"] = await self._create_alert(
                student_id, teacher_id, "LEVEL_UP", "MEDIUM",
                f"Recalibración sugerida: >90% de aciertos en las últimas {level_up_window} sesiones.",
                "Subir de nivel la ruta del alumno.",
            )
        elif len(accs) >= window:
            recent = list(reversed(accs))  # cronológico
            if recent[-1] <= recent[0] + 0.02:  # sin mejora en la ventana
                result["action"] = "stagnation"
                result["alert"] = await self._create_alert(
                    student_id, teacher_id, "STAGNATION", "HIGH",
                    f"Estancamiento: sin mejora en las últimas {window} sesiones.",
                    "Revisar la ruta y considerar apoyo adicional (TTS/segmentación).",
                )
        return result

    async def _create_alert(self, student_id, teacher_id, alert_type: str, urgency: str, message: str, suggested_action: str) -> dict | None:
        # Dedup: no repetir el mismo tipo de alerta no leída en las últimas 24h.
        existing = await self.session.execute(
            text(
                '''
                SELECT id FROM tracking.alerts
                WHERE student_id = :sid AND alert_type = :atype AND is_read = FALSE
                  AND created_at > now() - INTERVAL '24 hours'
                LIMIT 1
                '''
            ),
            {"sid": str(student_id), "atype": alert_type},
        )
        if existing.first():
            return None
        inserted = await self.session.execute(
            text(
                '''
                INSERT INTO tracking.alerts (student_id, teacher_id, alert_type, message, suggested_action, urgency)
                VALUES (:sid, :tid, :atype, :msg, :action, :urgency)
                RETURNING id, alert_type, urgency, message, created_at
                '''
            ),
            {"sid": str(student_id), "tid": str(teacher_id), "atype": alert_type,
             "msg": message, "action": suggested_action, "urgency": urgency},
        )
        return dict(inserted.mappings().one())
