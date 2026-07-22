from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.use_cases.payments.support import compute_license_expiry, map_conekta_status
from domain.exceptions.payment_exception import PlanNotFound
from domain.ports.payment_port import PaymentGatewayPort
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository


class CreateCardPaymentUseCase:
    """Checkout con tarjeta: el token ya viene tokenizado desde el cliente
    (mobile llama directo a la API pública de tokens de Conekta) — este caso
    de uso nunca ve un número de tarjeta, solo el token_id de un solo uso."""

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
        token_id: str,
    ) -> dict:
        plan = await self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFound(f"Plan {plan_id} no existe o no está activo")

        customer_id = await self._resolve_customer_id(school_id, admin_email, admin_name)

        idempotency_key = str(uuid4())
        payment = await self.repository.create_pending_payment(
            school_id=school_id,
            plan_id=plan_id,
            created_by_user_id=created_by_user_id,
            payment_method_type="card",
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            idempotency_key=idempotency_key,
        )

        order = await self.gateway.create_card_order(
            customer_id=customer_id,
            token_id=token_id,
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            description=f"CogniFit Escolar — {plan['name']}",
            idempotency_key=idempotency_key,
        )
        status = map_conekta_status(order["status"])
        paid_at = datetime.now(timezone.utc) if status == "paid" else None

        updated = await self.repository.attach_conekta_order(
            payment["id"],
            conekta_order_id=order["id"],
            status=status,
            paid_at=paid_at,
            raw_event=order["raw"],
        )

        if status == "paid":
            await self.repository.upgrade_school_license(
                school_id,
                license_tier=plan["license_tier"],
                expires_at=compute_license_expiry(plan["billing_period"]),
            )

        return updated

    async def _resolve_customer_id(self, school_id: UUID, email: str, name: str) -> str:
        customer_id = await self.repository.get_customer_id(school_id)
        if customer_id:
            return customer_id
        customer_id = await self.gateway.create_customer(email=email, name=name)
        await self.repository.save_customer_id(school_id, customer_id)
        return customer_id
