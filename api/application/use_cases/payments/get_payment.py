from __future__ import annotations

from uuid import UUID

from domain.exceptions.payment_exception import PaymentNotFound
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository


class GetPaymentUseCase:
    def __init__(self, repository: PgPaymentRepository) -> None:
        self.repository = repository

    async def execute(self, payment_id: UUID, *, school_id: UUID) -> dict:
        payment = await self.repository.get_payment(payment_id, school_id=school_id)
        if not payment:
            raise PaymentNotFound(f"Pago {payment_id} no encontrado")
        return payment
