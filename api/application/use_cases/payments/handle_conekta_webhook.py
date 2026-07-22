from __future__ import annotations

import logging
from datetime import datetime, timezone

from application.use_cases.payments.support import compute_license_expiry, map_conekta_status
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository

logger = logging.getLogger(__name__)

# Tipos de evento que nos importan. Conekta manda muchos otros (customer.*,
# subscription.*, ...) que no aplican a este flujo de pago único.
_RELEVANT_EVENT_TYPES = {
    "order.paid",
    "order.pending_payment_expired",
    "order.expired",
    "order.canceled",
    "charge.paid",
    "charge.declined",
}


class HandleConektaWebhookUseCase:
    """Procesa un evento de webhook de Conekta de forma idempotente: la firma
    ya se verificó en el router (ver api/v1/webhooks/router.py) antes de
    llegar aquí. billing.webhook_events.conekta_event_id es la clave que
    evita procesar el mismo evento dos veces si Conekta lo reintenta."""

    def __init__(self, repository: PgPaymentRepository) -> None:
        self.repository = repository

    async def execute(self, payload: dict) -> None:
        event_id = payload.get("id")
        event_type = payload.get("type", "")
        if not event_id:
            logger.warning("Webhook de Conekta sin id, se ignora: %s", payload)
            return

        is_new = await self.repository.record_webhook_event(event_id, event_type=event_type, payload=payload)
        if not is_new:
            logger.info("Webhook de Conekta %s ya procesado, se omite", event_id)
            return

        try:
            if event_type in _RELEVANT_EVENT_TYPES:
                await self._apply(event_type, payload)
            await self.repository.mark_webhook_processed(event_id)
        except Exception as exc:
            logger.exception("Error procesando webhook de Conekta %s", event_id)
            await self.repository.mark_webhook_processed(event_id, error=str(exc))
            raise

    async def _apply(self, event_type: str, payload: dict) -> None:
        order_data = payload.get("data", {}).get("object", {})
        order_id = order_data.get("id") if event_type.startswith("order.") else order_data.get("order_id")
        if not order_id:
            logger.warning("Webhook %s sin order id en payload: %s", event_type, payload)
            return

        status = map_conekta_status(order_data.get("payment_status")) if event_type.startswith("order.") else (
            "paid" if event_type == "charge.paid" else "failed"
        )
        paid_at = datetime.now(timezone.utc) if status == "paid" else None

        payment = await self.repository.mark_status_by_order_id(
            order_id, status=status, paid_at=paid_at, raw_event=payload
        )
        if payment and status == "paid":
            plan = await self.repository.get_plan(payment["plan_id"])
            if plan:
                await self.repository.upgrade_school_license(
                    payment["school_id"],
                    license_tier=plan["license_tier"],
                    expires_at=compute_license_expiry(plan["billing_period"]),
                )
