from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.exceptions.payment_exception import PlanNotFound
from domain.ports.payment_port import PaymentGatewayPort
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository


class CreateCashPaymentUseCase:
    """Checkout en efectivo (OXXO Pay). La orden siempre queda 'pending' al
    responder: no hay forma de saber si el ADMIN pagó hasta que Conekta
    mande el webhook order.paid (ver handle_conekta_webhook.py), minutos
    u horas después."""

    def __init__(self, repository: PgPaymentRepository, gateway: PaymentGatewayPort) -> None:
        self.repository = repository
        self.gateway = gateway

    async def execute(
        self,
        *,
        school_id: UUID,
        plan_id: UUID,
        created_by_user_id: UUID,
        admin_email: str,
        admin_name: str,
    ) -> dict:
        plan = await self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFound(f"Plan {plan_id} no existe o no está activo")

        customer_id = await self.repository.get_customer_id(school_id)
        if not customer_id:
            customer_id = await self.gateway.create_customer(email=admin_email, name=admin_name)
            await self.repository.save_customer_id(school_id, customer_id)

        idempotency_key = str(uuid4())
        payment = await self.repository.create_pending_payment(
            school_id=school_id,
            plan_id=plan_id,
            created_by_user_id=created_by_user_id,
            payment_method_type="cash",
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            idempotency_key=idempotency_key,
        )

        order = await self.gateway.create_cash_order(
            customer_id=customer_id,
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            description=f"CogniFit Escolar — {plan['name']}",
            idempotency_key=idempotency_key,
        )
        cash = order.get("cash", {})

        return await self.repository.attach_conekta_order(
            payment["id"],
            conekta_order_id=order["id"],
            status="pending",
            cash_reference=cash.get("reference"),
            cash_barcode_url=cash.get("barcode_url"),
            cash_expires_at=_parse_expires_at(cash.get("expires_at")),
            raw_event=order["raw"],
        )


def _parse_expires_at(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
