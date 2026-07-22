from __future__ import annotations

import hashlib
import hmac
import logging

from config.settings import get_settings
from domain.exceptions.payment_exception import PaymentGatewayNotConfigured
from infrastructure.conekta.conekta_client import ConektaClient

logger = logging.getLogger(__name__)


class ConektaPaymentAdapter:
    """Implementa PaymentGatewayPort traduciendo nuestro dominio (planes,
    montos en centavos, dos medios de pago) al formato de la API de Conekta.

    NOTA DE INTEGRACIÓN: la forma exacta del payload de /orders y el nombre
    del header de firma de webhook corresponden a la API v2.1.0 de Conekta
    documentada públicamente al momento de escribir esto. Antes de aceptar
    tráfico real, valida ambos contra una cuenta sandbox de Conekta (los
    campos de `charges[].payment_method` y el nombre del header de firma son
    los puntos que más cambian entre versiones de su API).
    """

    def __init__(self, client: ConektaClient | None = None) -> None:
        self.client = client or ConektaClient()
        self.settings = get_settings()

    async def create_customer(self, *, email: str, name: str) -> str:
        response = await self.client.create_customer(email=email, name=name)
        return response["id"]

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
        payload = {
            "currency": currency,
            "customer_info": {"customer_id": customer_id},
            "line_items": [{"name": description, "unit_price": amount_cents, "quantity": 1}],
            "charges": [{"payment_method": {"type": "card", "token_id": token_id}}],
        }
        order = await self.client.create_order(payload, idempotency_key=idempotency_key)
        return _normalize_order(order)

    async def create_cash_order(
        self,
        *,
        customer_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        idempotency_key: str,
    ) -> dict:
        payload = {
            "currency": currency,
            "customer_info": {"customer_id": customer_id},
            "line_items": [{"name": description, "unit_price": amount_cents, "quantity": 1}],
            # type "cash" resuelve a OXXO Pay para clientes MXN, que es el
            # único medio "efectivo" que ofrece Conekta.
            "charges": [{"payment_method": {"type": "cash"}}],
        }
        order = await self.client.create_order(payload, idempotency_key=idempotency_key)
        return _normalize_order(order)

    async def retrieve_order(self, conekta_order_id: str) -> dict:
        order = await self.client.get_order(conekta_order_id)
        return _normalize_order(order)

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str | None) -> bool:
        if not self.settings.conekta_webhook_secret:
            raise PaymentGatewayNotConfigured("CONEKTA_WEBHOOK_SECRET no está configurada en este entorno")
        if not signature_header:
            return False
        expected = hmac.new(
            self.settings.conekta_webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)


def _normalize_order(order: dict) -> dict:
    """Aplana la respuesta de Conekta a lo que los use cases necesitan,
    para no esparcir `order["charges"][0][...]` por toda la capa de aplicación."""
    charges = order.get("charges", {})
    charge_list = charges.get("data", charges) if isinstance(charges, dict) else charges
    first_charge = (charge_list or [{}])[0] if charge_list else {}
    payment_method = first_charge.get("payment_method", {})

    result = {
        "id": order["id"],
        "status": order.get("payment_status") or first_charge.get("status", "pending_payment"),
        "raw": order,
    }
    if payment_method.get("type") == "cash":
        result["cash"] = {
            "reference": payment_method.get("reference"),
            "barcode_url": payment_method.get("barcode_url"),
            "expires_at": payment_method.get("expires_at"),
        }
    return result
