from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgGroupRepository:
    """Grupos académicos (academic.groups). Un grupo pertenece a un docente y a
    una escuela. Para que un docente pueda crear grupos desde la app sin conocer
    UUIDs, se reutiliza/crea automáticamente una escuela por defecto."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_groups(self, teacher_id: UUID, is_admin: bool = False) -> list[dict]:
        where = "" if is_admin else "WHERE g.teacher_id = :teacher_id"
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
            {"teacher_id": str(teacher_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_group(self, teacher_id: UUID, data: dict) -> dict:
        school_id = await self._ensure_school(teacher_id, data.get("school_name"))
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
                "school_id": str(school_id),
                "teacher_id": str(teacher_id),
                "grade": data["grade"],
                "group_label": data["group_label"],
                "school_year": data["school_year"],
            },
        )
        row = dict(result.mappings().one())
        row["student_count"] = 0
        return row

    async def _ensure_school(self, teacher_id: UUID, school_name: str | None) -> UUID:
        """Reutiliza la escuela existente del docente (si ya tiene grupos);
        de lo contrario crea una escuela por defecto para él."""
        existing = await self.session.execute(
            text(
                '''
                SELECT school_id FROM academic.groups
                WHERE teacher_id = :teacher_id
                ORDER BY created_at
                LIMIT 1
                '''
            ),
            {"teacher_id": str(teacher_id)},
        )
        row = existing.mappings().first()
        if row:
            return row["school_id"]

        created = await self.session.execute(
            text(
                '''
                INSERT INTO academic.schools (name)
                VALUES (:name)
                RETURNING id
                '''
            ),
            {"name": school_name or "Escuela CogniFit"},
        )
        return created.mappings().one()["id"]
