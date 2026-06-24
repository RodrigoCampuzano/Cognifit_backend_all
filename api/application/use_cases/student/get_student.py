from __future__ import annotations

from uuid import UUID

from domain.exceptions.student_exception import StudentNotFound
from infrastructure.database.repositories.pg_student_repository import PgStudentRepository


class GetStudentUseCase:
    def __init__(self, repository: PgStudentRepository) -> None:
        self.repository = repository

    async def execute(self, student_id: UUID) -> dict:
        student = await self.repository.get_student(student_id)
        if not student:
            raise StudentNotFound("Student not found")
        return student
