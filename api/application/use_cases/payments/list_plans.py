from __future__ import annotations

from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository


class ListPlansUseCase:
    def __init__(self, repository: PgPaymentRepository) -> None:
        self.repository = repository

    async def execute(self) -> list[dict]:
        return await self.repository.list_active_plans()
