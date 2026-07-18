from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.events.progress_evaluated import ProgressEvaluated


async def create_alert_on_high_risk(
    session: AsyncSession, *, student_id, pln_subtype: str | None, pln_severity: str | None,
    risk_level: str | None, risk_probability: float | None,
) -> dict | None:
    """Crea una alerta para el docente cuando un diagnóstico sale de riesgo alto.

    Antes el diagnóstico no publicaba ningún evento ni generaba alerta: un
    alumno con riesgo HIGH solo se descubría si alguien abría manualmente su
    perfil. Las alertas por estancamiento/nivel sí existían (vía
    ProgressEvaluated), pero venían del seguimiento de intervención, no del
    tamizaje.

    El docente se resuelve desde el grupo del alumno. Deduplica igual que las
    demás alertas: no repite una HIGH_RISK no leída de las últimas 24h.
    """
    if (risk_level or "").upper() != "HIGH":
        return None

    teacher = await session.execute(
        text(
            '''
            SELECT g.teacher_id FROM academic.students s
            JOIN academic.groups g ON g.id = s.group_id
            WHERE s.id = :sid
            '''
        ),
        {"sid": str(student_id)},
    )
    row = teacher.first()
    if not row or not row[0]:
        return None
    teacher_id = row[0]

    existing = await session.execute(
        text(
            '''
            SELECT id FROM tracking.alerts
            WHERE student_id = :sid AND alert_type = 'HIGH_RISK' AND is_read = FALSE
              AND created_at > now() - INTERVAL '24 hours'
            LIMIT 1
            '''
        ),
        {"sid": str(student_id)},
    )
    if existing.first():
        return None

    pct = f"{round((risk_probability or 0) * 100)}%"
    perfil = " / ".join(x for x in (pln_subtype, pln_severity) if x) or "sin clasificar"
    inserted = await session.execute(
        text(
            '''
            INSERT INTO tracking.alerts (student_id, teacher_id, alert_type, message, suggested_action, urgency)
            VALUES (:sid, :tid, 'HIGH_RISK', :msg, :action, 'HIGH')
            RETURNING id, alert_type, urgency, message, created_at
            '''
        ),
        {
            "sid": str(student_id),
            "tid": str(teacher_id),
            "msg": f"Tamizaje con riesgo alto ({pct}). Perfil: {perfil}.",
            "action": "Revisa el perfil del alumno y canaliza a valoración con especialista.",
        },
    )
    return dict(inserted.mappings().one())


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
