from __future__ import annotations

import base64
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from config.settings import get_settings
from domain.exceptions.payment_exception import PaymentGatewayNotConfigured
from infrastructure.conekta.conekta_client import ConektaClient

logger = logging.getLogger(__name__)


class ConektaPaymentAdapter:
    """Implementa PaymentGatewayPort traduciendo nuestro dominio (planes,
    montos en centavos, tres medios de pago) al formato de la API de Conekta.

    NOTA DE INTEGRACIÓN: la forma exacta del payload de /orders corresponde a
    la API v2.1.0 de Conekta documentada públicamente al momento de escribir
    esto — antes de aceptar tráfico real, valida los campos de
    `charges[].payment_method` contra una cuenta sandbox (son el punto que
    más cambia entre versiones de su API). La verificación de firma de
    webhook sí está confirmada contra developers.conekta.com/docs/autenticacion-webhooks:
    header `Digest`, RSA-SHA256 (PKCS1v15) sobre el body crudo en UTF-8, con
    la llave pública que Conekta entrega al inicializar POST /webhook_keys.
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

    async def create_spei_order(
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
            "charges": [{"payment_method": {"type": "spei"}}],
        }
        order = await self.client.create_order(payload, idempotency_key=idempotency_key)
        return _normalize_order(order)

    async def retrieve_order(self, conekta_order_id: str) -> dict:
        order = await self.client.get_order(conekta_order_id)
        return _normalize_order(order)

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str | None) -> bool:
        """Conekta firma cada webhook con su llave PRIVADA y manda la firma en
        el header Digest (base64, RSA-SHA256 sobre el body crudo). Acá se
        verifica con la llave PÚBLICA correspondiente — nunca al revés."""
        if not self.settings.conekta_webhook_public_key:
            raise PaymentGatewayNotConfigured("CONEKTA_WEBHOOK_PUBLIC_KEY no está configurada en este entorno")
        if not signature_header:
            return False
        try:
            signature = base64.b64decode(signature_header, validate=True)
        except (ValueError, TypeError):
            return False

        public_key = serialization.load_pem_public_key(self.settings.conekta_webhook_public_key.encode())
        if not isinstance(public_key, RSAPublicKey):
            raise PaymentGatewayNotConfigured("CONEKTA_WEBHOOK_PUBLIC_KEY no es una llave pública RSA")

        try:
            public_key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
            return True
        except InvalidSignature:
            return False


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
    if payment_method.get("type") == "spei":
        result["spei"] = {
            "clabe": payment_method.get("clabe"),
            "bank": payment_method.get("bank"),
            "expires_at": payment_method.get("expires_at"),
        }
    return result
