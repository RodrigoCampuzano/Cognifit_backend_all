from __future__ import annotations

from uuid import UUID

from application.services.screening_service import ScreeningService
from infrastructure.database.repositories.pg_session_repository import PgSessionRepository


class StartScreeningUseCase:
    def __init__(self, repository: PgSessionRepository, screening: ScreeningService) -> None:
        self.repository = repository
        self.screening = screening

    async def execute(self, *, student_id: UUID, teacher_id: UUID, teacher_score: float, risk_flags: list[dict]) -> list[dict]:
        module_codes = self.screening.enabled_modules(teacher_score)
        return await self.repository.create_assignments(
            student_id=student_id,
            module_codes=module_codes,
            teacher_id=teacher_id,
            teacher_score=teacher_score,
            risk_flags=risk_flags,
        )
