from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import get_db
from api.dependencies.services import get_payment_gateway
from application.use_cases.payments.handle_conekta_webhook import HandleConektaWebhookUseCase
from domain.exceptions.payment_exception import PaymentGatewayNotConfigured
from domain.ports.payment_port import PaymentGatewayPort
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# NOTA DE INTEGRACIÓN: confirma el nombre real de este header contra el panel
# de configuración de webhooks de tu cuenta Conekta antes de producción — es
# el punto más propenso a cambiar entre cuentas/versiones de su API.
_SIGNATURE_HEADER = "X-Conekta-Signature"


@router.post("/conekta", status_code=200, include_in_schema=False)
async def receive_conekta_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    gateway: PaymentGatewayPort = Depends(get_payment_gateway),
    signature: str | None = Header(default=None, alias=_SIGNATURE_HEADER),
):
    """Endpoint público (sin JWT) que recibe eventos de Conekta. La
    autenticidad no viene de un Authorization header sino de la firma del
    cuerpo — por eso se lee el body crudo ANTES de que nada lo parsee, y se
    verifica contra CONEKTA_WEBHOOK_SECRET antes de confiar en el payload."""
    raw_body = await request.body()

    try:
        if not gateway.verify_webhook_signature(payload=raw_body, signature_header=signature):
            raise HTTPException(status_code=401, detail="Firma de webhook inválida")
    except PaymentGatewayNotConfigured as exc:
        # Entorno sin CONEKTA_WEBHOOK_SECRET (dev/test): no hay nada que
        # verificar contra, así que no podemos aceptar webhooks reales.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload no es JSON válido") from exc

    await HandleConektaWebhookUseCase(PgPaymentRepository(db)).execute(payload)
    return {"received": True}
