from __future__ import annotations

from uuid import UUID

from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository


class ListPaymentsUseCase:
    def __init__(self, repository: PgPaymentRepository) -> None:
        self.repository = repository

    async def execute(self, *, school_id: UUID) -> list[dict]:
        return await self.repository.list_by_school(school_id)
