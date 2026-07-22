from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgPaymentRepository:
    """Persistencia de planes, pagos y el mapeo escuela↔customer de Conekta.

    Sigue el mismo estilo que pg_institution_repository.py: SQL parametrizado
    directo (sin ORM declarativo), y filtrado explícito por school_id en cada
    query en vez de depender de RLS (billing.* no tiene RLS habilitado, igual
    que academic.schools)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Planes ───────────────────────────────────────────────────────────────

    async def list_active_plans(self) -> list[dict]:
        result = await self.session.execute(
            text(
                """
                SELECT id, code, name, license_tier, price_cents, currency, billing_period, features
                FROM billing.plans
                WHERE is_active = TRUE
                ORDER BY price_cents ASC
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_plan(self, plan_id: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, code, name, license_tier, price_cents, currency, billing_period, features
                FROM billing.plans
                WHERE id = :id AND is_active = TRUE
                """
            ),
            {"id": str(plan_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    # ── Customer de Conekta por escuela ─────────────────────────────────────

    async def get_customer_id(self, school_id: UUID) -> str | None:
        result = await self.session.execute(
            text("SELECT conekta_customer_id FROM billing.school_conekta_customers WHERE school_id = :id"),
            {"id": str(school_id)},
        )
        row = result.first()
        return row[0] if row else None

    async def save_customer_id(self, school_id: UUID, conekta_customer_id: str) -> None:
        await self.session.execute(
            text(
                """
                INSERT INTO billing.school_conekta_customers (school_id, conekta_customer_id)
                VALUES (:school_id, :customer_id)
                ON CONFLICT (school_id) DO UPDATE SET conekta_customer_id = EXCLUDED.conekta_customer_id
                """
            ),
            {"school_id": str(school_id), "customer_id": conekta_customer_id},
        )

    # ── Pagos ────────────────────────────────────────────────────────────────

    async def create_pending_payment(
        self,
        *,
        school_id: UUID,
        plan_id: UUID,
        created_by_user_id: UUID,
        payment_method_type: str,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        result = await self.session.execute(
            text(
                """
                INSERT INTO billing.payments
                    (school_id, plan_id, created_by_user_id, payment_method_type,
                     amount_cents, currency, idempotency_key)
                VALUES (:school_id, :plan_id, :created_by, :method, :amount, :currency, :idem_key)
                RETURNING id, school_id, plan_id, payment_method_type, status, amount_cents,
                          currency, cash_reference, cash_barcode_url, cash_expires_at,
                          paid_at, idempotency_key, created_at
                """
            ),
            {
                "school_id": str(school_id),
                "plan_id": str(plan_id),
                "created_by": str(created_by_user_id),
                "method": payment_method_type,
                "amount": amount_cents,
                "currency": currency,
                "idem_key": idempotency_key,
            },
        )
        return dict(result.mappings().one())

    async def attach_conekta_order(
        self,
        payment_id: UUID,
        *,
        conekta_order_id: str,
        status: str,
        cash_reference: str | None = None,
        cash_barcode_url: str | None = None,
        cash_expires_at: datetime | None = None,
        paid_at: datetime | None = None,
        raw_event: dict | None = None,
    ) -> dict:
        result = await self.session.execute(
            text(
                """
                UPDATE billing.payments
                   SET conekta_order_id = :order_id,
                       status = :status,
                       cash_reference = COALESCE(:cash_reference, cash_reference),
                       cash_barcode_url = COALESCE(:cash_barcode_url, cash_barcode_url),
                       cash_expires_at = COALESCE(:cash_expires_at, cash_expires_at),
                       paid_at = COALESCE(:paid_at, paid_at),
                       raw_last_event = COALESCE(CAST(:raw_event AS jsonb), raw_last_event)
                 WHERE id = :id
                RETURNING id, school_id, plan_id, payment_method_type, status, amount_cents,
                          currency, cash_reference, cash_barcode_url, cash_expires_at,
                          paid_at, idempotency_key, created_at
                """
            ),
            {
                "id": str(payment_id),
                "order_id": conekta_order_id,
                "status": status,
                "cash_reference": cash_reference,
                "cash_barcode_url": cash_barcode_url,
                "cash_expires_at": cash_expires_at,
                "paid_at": paid_at,
                "raw_event": _to_jsonb(raw_event),
            },
        )
        return dict(result.mappings().one())

    async def get_payment(self, payment_id: UUID, *, school_id: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, school_id, plan_id, payment_method_type, status, amount_cents,
                       currency, cash_reference, cash_barcode_url, cash_expires_at,
                       paid_at, created_at
                FROM billing.payments
                WHERE id = :id AND school_id = :school_id
                """
            ),
            {"id": str(payment_id), "school_id": str(school_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_by_conekta_order_id(self, conekta_order_id: str) -> dict | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, school_id, plan_id, payment_method_type, status, amount_cents,
                       currency, created_at
                FROM billing.payments
                WHERE conekta_order_id = :order_id
                """
            ),
            {"order_id": conekta_order_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def list_by_school(self, school_id: UUID) -> list[dict]:
        result = await self.session.execute(
            text(
                """
                SELECT id, plan_id, payment_method_type, status, amount_cents, currency,
                       cash_reference, cash_expires_at, paid_at, created_at
                FROM billing.payments
                WHERE school_id = :school_id
                ORDER BY created_at DESC
                """
            ),
            {"school_id": str(school_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def mark_status_by_order_id(
        self, conekta_order_id: str, *, status: str, paid_at: datetime | None, raw_event: dict
    ) -> dict | None:
        result = await self.session.execute(
            text(
                """
                UPDATE billing.payments
                   SET status = :status,
                       paid_at = COALESCE(:paid_at, paid_at),
                       raw_last_event = CAST(:raw_event AS jsonb)
                 WHERE conekta_order_id = :order_id
                RETURNING id, school_id, plan_id, status
                """
            ),
            {"order_id": conekta_order_id, "status": status, "paid_at": paid_at, "raw_event": _to_jsonb(raw_event)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    # ── Licencia de la escuela ───────────────────────────────────────────────

    async def upgrade_school_license(self, school_id: UUID, *, license_tier: str, expires_at: datetime) -> None:
        await self.session.execute(
            text(
                """
                UPDATE academic.schools
                   SET license_tier = :tier, license_expires_at = :expires_at
                 WHERE id = :id
                """
            ),
            {"id": str(school_id), "tier": license_tier, "expires_at": expires_at},
        )

    # ── Idempotencia de webhooks ─────────────────────────────────────────────

    async def has_processed_webhook_event(self, conekta_event_id: str) -> bool:
        result = await self.session.execute(
            text("SELECT 1 FROM billing.webhook_events WHERE conekta_event_id = :id"),
            {"id": conekta_event_id},
        )
        return result.first() is not None

    async def record_webhook_event(self, conekta_event_id: str, *, event_type: str, payload: dict) -> bool:
        """Inserta el evento si es nuevo. Devuelve False si ya existía (ON
        CONFLICT DO NOTHING) para que el use case pueda saltarse el
        procesamiento sin una segunda consulta."""
        result = await self.session.execute(
            text(
                """
                INSERT INTO billing.webhook_events (conekta_event_id, event_type, payload)
                VALUES (:id, :event_type, CAST(:payload AS jsonb))
                ON CONFLICT (conekta_event_id) DO NOTHING
                RETURNING id
                """
            ),
            {"id": conekta_event_id, "event_type": event_type, "payload": _to_jsonb(payload)},
        )
        return result.first() is not None

    async def mark_webhook_processed(self, conekta_event_id: str, *, error: str | None = None) -> None:
        await self.session.execute(
            text(
                """
                UPDATE billing.webhook_events
                   SET processed_at = now(), processing_error = :error
                 WHERE conekta_event_id = :id
                """
            ),
            {"id": conekta_event_id, "error": error},
        )


def _to_jsonb(value: dict | None) -> str | None:
    return json.dumps(value) if value is not None else None
