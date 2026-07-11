from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgGroupRepository:
    """Grupos académicos (academic.groups). Un grupo pertenece a un docente y a
    una escuela — la institución del creador, nunca autogenerada (ver ADR de
    multi-tenancy: antes cada docente sin escuela previa generaba una nueva
    fila de "Escuela CogniFit", fragmentando el piloto en escuelas duplicadas)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_groups(self, teacher_id: UUID, *, institution_id: UUID, is_privileged: bool = False) -> list[dict]:
        conditions = ["g.school_id = :institution_id"]
        params: dict = {"institution_id": str(institution_id)}
        if not is_privileged:
            conditions.append("g.teacher_id = :teacher_id")
            params["teacher_id"] = str(teacher_id)
        where = f"WHERE {' AND '.join(conditions)}"
        result = await self.session.execute(
            text(
                f'''
                SELECT
                    g.id, g.grade, g.group_label, g.school_year, g.is_active,
                    COUNT(s.id) FILTER (WHERE s.is_active) AS student_count
                FROM academic.groups g
                LEFT JOIN academic.students s ON s.group_id = g.id
                {where}
                GROUP BY g.id
                ORDER BY g.grade, g.group_label
                '''
            ),
            params,
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_group(self, teacher_id: UUID, institution_id: UUID, data: dict) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO academic.groups (school_id, teacher_id, grade, group_label, school_year)
                VALUES (:school_id, :teacher_id, :grade, :group_label, :school_year)
                ON CONFLICT (school_id, grade, group_label, school_year) DO UPDATE
                    SET is_active = TRUE
                RETURNING id, grade, group_label, school_year, is_active
                '''
            ),
            {
                "school_id": str(institution_id),
                "teacher_id": str(teacher_id),
                "grade": data["grade"],
                "group_label": data["group_label"],
                "school_year": data["school_year"],
            },
        )
        row = dict(result.mappings().one())
        row["student_count"] = 0
        return row

    async def delete_group(self, group_id: UUID, *, institution_id: UUID) -> None:
        """Elimina el grupo sólo si pertenece a la institución del solicitante
        y no tiene alumnos (activos o no). Lanza ValueError en ambos casos de
        rechazo para que el router devuelva 404/409 según corresponda."""
        group = await self.session.execute(
            text("SELECT id FROM academic.groups WHERE id = :gid AND school_id = :institution_id"),
            {"gid": str(group_id), "institution_id": str(institution_id)},
        )
        if group.first() is None:
            raise LookupError("Group not found")
        count_result = await self.session.execute(
            text("SELECT COUNT(*) FROM academic.students WHERE group_id = :gid"),
            {"gid": str(group_id)},
        )
        count = count_result.scalar_one()
        if count > 0:
            raise ValueError(f"El grupo tiene {count} alumno(s); muévelos antes de eliminarlo.")
        await self.session.execute(
            text("DELETE FROM academic.groups WHERE id = :gid"),
            {"gid": str(group_id)},
        )
