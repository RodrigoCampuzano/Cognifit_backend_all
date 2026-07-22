from __future__ import annotations

from typing import Protocol


class PaymentGatewayPort(Protocol):
    """Puerto hacia la pasarela de pagos externa (Conekta). Implementado por
    infrastructure/conekta/conekta_payment_adapter.py.

    Deliberadamente no conoce billing.payments ni academic.schools: la
    persistencia y la orquestación (reutilizar customer_id, marcar el pago
    como pagado, actualizar la licencia) viven en los use cases. Este puerto
    solo habla con la pasarela.
    """

    async def create_customer(self, *, email: str, name: str) -> str:
        """Crea un customer en la pasarela y devuelve su id."""
        ...

    async def create_card_order(
        self,
        *,
        customer_id: str,
        token_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        idempotency_key: str,
    ) -> dict:
        """Crea una orden con cargo a tarjeta ya tokenizada. Devuelve la
        respuesta de la pasarela con al menos {id, status: 'paid'|'pending_payment'|...}."""
        ...

    async def create_cash_order(
        self,
        *,
        customer_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        idempotency_key: str,
    ) -> dict:
        """Crea una orden de pago en efectivo (OXXO). Devuelve la respuesta de
        la pasarela con {id, status, cash: {reference, barcode_url, expires_at}}."""
        ...

    async def retrieve_order(self, conekta_order_id: str) -> dict:
        ...

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str | None) -> bool:
        """Valida que un webhook entrante realmente venga de la pasarela."""
        ...
