from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Estados que Conekta puede devolver en order.payment_status / order.paid, etc.
# Se colapsan a los cinco valores que acepta billing.payments.status.
_CONEKTA_STATUS_MAP = {
    "paid": "paid",
    "declined": "failed",
    "expired": "expired",
    "canceled": "canceled",
    "refunded": "refunded",
    "partially_refunded": "refunded",
    "pending_payment": "pending",
    "partially_paid": "pending",
}


def map_conekta_status(conekta_status: str | None) -> str:
    return _CONEKTA_STATUS_MAP.get(conekta_status or "", "pending")


def compute_license_expiry(billing_period: str, *, from_: datetime | None = None) -> datetime:
    start = from_ or datetime.now(timezone.utc)
    days = 365 if billing_period == "yearly" else 30
    return start + timedelta(days=days)
