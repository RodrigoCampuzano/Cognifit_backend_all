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

    async def permanent_delete_student(self, student_id: UUID) -> bool:
        """Borrado físico irreversible. Elimina todos los datos del alumno en orden
        para respetar las FK NO ACTION antes de borrar la fila raíz."""
        sid = str(student_id)
        # Verificar que existe (y que está inactivo — capa extra de seguridad)
        check = await self.session.execute(
            text("SELECT id, is_active FROM academic.students WHERE id=:id"),
            {"id": sid},
        )
        row = check.mappings().first()
        if not row:
            return False

        # 1. progress_snapshots (referencia student_id y student_path_id)
        await self.session.execute(
            text("DELETE FROM tracking.progress_snapshots WHERE student_id=:id"),
            {"id": sid},
        )
        # 2. exercise_sessions → a través de student_paths
        await self.session.execute(
            text("""
                DELETE FROM intervention.exercise_sessions
                WHERE student_path_id IN (
                    SELECT id FROM intervention.student_paths WHERE student_id=:id
                )
            """),
            {"id": sid},
        )
        # 3. alerts
        await self.session.execute(
            text("DELETE FROM tracking.alerts WHERE student_id=:id"),
            {"id": sid},
        )
        # 4. report_requests
        await self.session.execute(
            text("DELETE FROM reporting.report_requests WHERE student_id=:id"),
            {"id": sid},
        )
        # 5. diagnoses (FK NO ACTION a student y a test_assignments)
        await self.session.execute(
            text("DELETE FROM diagnosis.diagnoses WHERE student_id=:id"),
            {"id": sid},
        )
        # 6. student_paths
        await self.session.execute(
            text("DELETE FROM intervention.student_paths WHERE student_id=:id"),
            {"id": sid},
        )
        # 7. test_assignments → en cascada: test_sessions y student_responses
        await self.session.execute(
            text("DELETE FROM assessment.test_assignments WHERE student_id=:id"),
            {"id": sid},
        )
        # 8. student (en cascada: teacher_screening_results, guardian_consents, diagnosis_ml_sessions)
        result = await self.session.execute(
            text("DELETE FROM academic.students WHERE id=:id RETURNING id"),
            {"id": sid},
        )
        return result.mappings().first() is not None

    async def get_linked_student(self, user_id: UUID) -> dict | None:
        """Devuelve el alumno cuya cuenta propia (user_id) o cuyo padre (parent_user_id) coincide con user_id."""
        result = await self.session.execute(
            text(
                """
                SELECT
                    s.id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS full_name,
                    s.group_id
                FROM academic.students s
                WHERE (s.user_id = :uid OR s.parent_user_id = :uid)
                  AND s.is_active = TRUE
                LIMIT 1
                """
            ),
            {"uid": str(user_id), "key": self.settings.db_encryption_key},
        )
        row = result.mappings().first()
        return dict(row) if row else None

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
