from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


class PgStudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def list_students(
        self,
        requester_id: UUID,
        *,
        is_privileged: bool,
        institution_id: UUID,
        group_id: UUID | None = None,
        grade: int | None = None,
    ) -> list[dict]:
        """Query Object: un TEACHER solo ve alumnos de sus propios grupos;
        ADMIN/SPECIALIST ven todos los de su institución — nunca de otras
        instituciones. Sin institution_id, cualquier ADMIN/SPECIALIST veía
        alumnos de todas las escuelas del sistema."""
        conditions: list[str] = ["g.school_id = :institution_id"]
        params: dict = {"key": self.settings.db_encryption_key, "institution_id": str(institution_id)}
        if not is_privileged:
            conditions.append("g.teacher_id = :teacher_id")
            params["teacher_id"] = str(requester_id)
        if group_id:
            conditions.append("s.group_id = :group_id")
            params["group_id"] = str(group_id)
        if grade is not None:
            conditions.append("g.grade = :grade")
            params["grade"] = grade
        where = f"WHERE {' AND '.join(conditions)}"
        result = await self.session.execute(
            text(
                f'''
                SELECT
                    s.id, s.group_id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS full_name,
                    s.birth_year, s.gender, s.is_active, s.enrolled_at
                FROM academic.students s
                JOIN academic.groups g ON g.id = s.group_id
                {where}
                ORDER BY s.enrolled_at DESC
                LIMIT 200
                '''
            ),
            params,
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_student(
        self, student_id: UUID, *, requester_id: UUID, is_privileged: bool, institution_id: UUID
    ) -> dict | None:
        """Verifica pertenencia antes de devolver el alumno: institución
        siempre, y además docente/padre propietario si no es privilegiado.
        Sin esto, cualquier rol autorizado podía leer cualquier alumno del
        sistema adivinando su UUID (IDOR)."""
        result = await self.session.execute(
            text(
                '''
                SELECT
                    s.id, s.group_id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS full_name,
                    s.birth_year, s.gender, s.is_active, s.enrolled_at
                FROM academic.students s
                JOIN academic.groups g ON g.id = s.group_id
                WHERE s.id = :student_id
                  AND g.school_id = :institution_id
                  AND (
                      :is_privileged
                      OR g.teacher_id = :requester_id
                      OR s.parent_user_id = :requester_id
                      OR s.user_id = :requester_id
                  )
                '''
            ),
            {
                "student_id": str(student_id),
                "key": self.settings.db_encryption_key,
                "institution_id": str(institution_id),
                "is_privileged": is_privileged,
                "requester_id": str(requester_id),
            },
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def link_parent_to_student(self, parent_user_id: UUID, student_id: UUID, *, institution_id: UUID) -> bool:
        """Vincula la cuenta de un padre/tutor al alumno indicado, verificando
        que ambos pertenezcan a la institución del admin solicitante.
        Primero borra cualquier vínculo previo de este padre con otro alumno."""
        parent_check = await self.session.execute(
            text("SELECT 1 FROM auth.users WHERE id = :uid AND institution_id = :institution_id AND role = 'PARENT'"),
            {"uid": str(parent_user_id), "institution_id": str(institution_id)},
        )
        if parent_check.first() is None:
            return False

        await self.session.execute(
            text("UPDATE academic.students SET parent_user_id = NULL WHERE parent_user_id = :uid"),
            {"uid": str(parent_user_id)},
        )
        result = await self.session.execute(
            text(
                '''
                UPDATE academic.students s SET parent_user_id = :uid
                FROM academic.groups g
                WHERE s.id = :sid AND g.id = s.group_id AND g.school_id = :institution_id
                RETURNING s.id
                '''
            ),
            {"uid": str(parent_user_id), "sid": str(student_id), "institution_id": str(institution_id)},
        )
        return result.mappings().first() is not None

    async def deactivate_student(self, student_id: UUID, *, institution_id: UUID) -> bool:
        result = await self.session.execute(
            text(
                '''
                UPDATE academic.students s SET is_active=FALSE
                FROM academic.groups g
                WHERE s.id=:id AND s.is_active=TRUE AND g.id = s.group_id AND g.school_id = :institution_id
                RETURNING s.id
                '''
            ),
            {"id": str(student_id), "institution_id": str(institution_id)},
        )
        return result.mappings().first() is not None

    async def activate_student(self, student_id: UUID, *, institution_id: UUID) -> bool:
        result = await self.session.execute(
            text(
                '''
                UPDATE academic.students s SET is_active=TRUE
                FROM academic.groups g
                WHERE s.id=:id AND s.is_active=FALSE AND g.id = s.group_id AND g.school_id = :institution_id
                RETURNING s.id
                '''
            ),
            {"id": str(student_id), "institution_id": str(institution_id)},
        )
        return result.mappings().first() is not None

    async def permanent_delete_student(self, student_id: UUID, *, institution_id: UUID) -> bool:
        """Borrado físico irreversible. Elimina todos los datos del alumno en orden
        para respetar las FK NO ACTION antes de borrar la fila raíz."""
        sid = str(student_id)
        # Verificar que existe, está inactivo y pertenece a la institución del solicitante.
        check = await self.session.execute(
            text(
                '''
                SELECT s.id, s.is_active FROM academic.students s
                JOIN academic.groups g ON g.id = s.group_id
                WHERE s.id=:id AND g.school_id = :institution_id
                '''
            ),
            {"id": sid, "institution_id": str(institution_id)},
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

    async def register_student(
        self, data: dict, *, requester_id: UUID, is_privileged: bool, institution_id: UUID
    ) -> dict:
        """Verifica que el group_id pertenezca a la institución (y, si no es
        privilegiado, al docente) del solicitante antes de crear el alumno —
        sin esto, cualquier TEACHER podía crear alumnos en el grupo de otra
        institución pasando su UUID directamente."""
        group_check = await self.session.execute(
            text(
                '''
                SELECT 1 FROM academic.groups
                WHERE id = :group_id AND school_id = :institution_id
                  AND (:is_privileged OR teacher_id = :requester_id)
                '''
            ),
            {
                "group_id": str(data["group_id"]),
                "institution_id": str(institution_id),
                "is_privileged": is_privileged,
                "requester_id": str(requester_id),
            },
        )
        if group_check.first() is None:
            raise ValueError("Group not found")

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
