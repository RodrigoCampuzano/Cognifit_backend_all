from __future__ import annotations

from application.dtos.student_dto import RegisterStudentDto
from infrastructure.database.repositories.pg_student_repository import PgStudentRepository


class RegisterStudentUseCase:
    def __init__(self, repository: PgStudentRepository) -> None:
        self.repository = repository

    async def execute(self, dto: RegisterStudentDto) -> dict:
        return await self.repository.register_student(dto.model_dump())
