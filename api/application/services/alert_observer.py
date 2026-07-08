from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.events.progress_evaluated import ProgressEvaluated


async def create_alert_on_progress_evaluated(session: AsyncSession, event: ProgressEvaluated) -> dict | None:
    """Observer: reacciona a ProgressEvaluated creando la alerta correspondiente.
    Deduplica: no repite el mismo tipo de alerta no leída en las últimas 24h."""
    if event.action not in ("stagnation", "level_up"):
        return None
    alert_type = "STAGNATION" if event.action == "stagnation" else "LEVEL_UP"

    existing = await session.execute(
        text(
            '''
            SELECT id FROM tracking.alerts
            WHERE student_id = :sid AND alert_type = :atype AND is_read = FALSE
              AND created_at > now() - INTERVAL '24 hours'
            LIMIT 1
            '''
        ),
        {"sid": str(event.student_id), "atype": alert_type},
    )
    if existing.first():
        return None

    inserted = await session.execute(
        text(
            '''
            INSERT INTO tracking.alerts (student_id, teacher_id, alert_type, message, suggested_action, urgency)
            VALUES (:sid, :tid, :atype, :msg, :action, :urgency)
            RETURNING id, alert_type, urgency, message, created_at
            '''
        ),
        {
            "sid": str(event.student_id),
            "tid": str(event.teacher_id),
            "atype": alert_type,
            "msg": event.message,
            "action": event.suggested_action,
            "urgency": event.urgency,
        },
    )
    return dict(inserted.mappings().one())
