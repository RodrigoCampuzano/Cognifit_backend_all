from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


class PgStudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def list_students(self, group_id: UUID | None = None) -> list[dict]:
        where = "WHERE s.group_id=:group_id" if group_id else ""
        result = await self.session.execute(
            text(
                f'''
                SELECT
                    s.id, s.group_id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS full_name,
                    s.birth_year, s.gender, s.is_active, s.enrolled_at
                FROM academic.students s
                {where}
                ORDER BY s.enrolled_at DESC
                LIMIT 200
                '''
            ),
            {"group_id": str(group_id) if group_id else None, "key": self.settings.db_encryption_key},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_student(self, student_id: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                SELECT
                    s.id, s.group_id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS full_name,
                    s.birth_year, s.gender, s.is_active, s.enrolled_at
                FROM academic.students s
                WHERE s.id=:student_id
                '''
            ),
            {"student_id": str(student_id), "key": self.settings.db_encryption_key},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def deactivate_student(self, student_id: UUID) -> bool:
        result = await self.session.execute(
            text("UPDATE academic.students SET is_active=FALSE WHERE id=:id AND is_active=TRUE RETURNING id"),
            {"id": str(student_id)},
        )
        return result.mappings().first() is not None

    async def activate_student(self, student_id: UUID) -> bool:
        result = await self.session.execute(
            text("UPDATE academic.students SET is_active=TRUE WHERE id=:id AND is_active=FALSE RETURNING id"),
            {"id": str(student_id)},
        )
        return result.mappings().first() is not None

    async def register_student(self, data: dict) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO academic.students (group_id, full_name, birth_year, gender)
                VALUES (:group_id, pgp_sym_encrypt(:full_name, :key), :birth_year, :gender)
                RETURNING id, group_id, pgp_sym_decrypt(full_name, :key)::text AS full_name, birth_year, gender, is_active, enrolled_at
                '''
            ),
            {
                "group_id": str(data["group_id"]),
                "full_name": data["full_name"],
                "birth_year": data.get("birth_year"),
                "gender": data.get("gender"),
                "key": self.settings.db_encryption_key,
            },
        )
        return dict(result.mappings().one())
