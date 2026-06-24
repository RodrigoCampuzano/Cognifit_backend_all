from __future__ import annotations

from uuid import UUID

from infrastructure.database.repositories.pg_student_repository import PgStudentRepository


class ListStudentsUseCase:
    def __init__(self, repository: PgStudentRepository) -> None:
        self.repository = repository

    async def execute(self, group_id: UUID | None = None) -> list[dict]:
        return await self.repository.list_students(group_id)
