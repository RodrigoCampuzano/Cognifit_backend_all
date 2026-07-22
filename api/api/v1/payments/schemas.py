from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    license_tier: str
    price_cents: int
    currency: str
    billing_period: str
    features: dict


class CardCheckoutRequest(BaseModel):
    plan_id: UUID
    # Token de un solo uso devuelto por POST https://api.conekta.io/tokens
    # (llamado directo desde el cliente con la llave pública). El número de
    # tarjeta nunca llega a este backend.
    token_id: str = Field(..., min_length=4)


class CashCheckoutRequest(BaseModel):
    plan_id: UUID


class PaymentResponse(BaseModel):
    id: UUID
    plan_id: UUID
    payment_method_type: str
    status: str
    amount_cents: int
    currency: str
    cash_reference: str | None = None
    cash_barcode_url: str | None = None
    cash_expires_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime
