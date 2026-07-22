"""HandleConektaWebhookUseCase: idempotencia (un evento no se procesa dos
veces) y actualización de licencia cuando el evento es order.paid."""
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from application.use_cases.payments.handle_conekta_webhook import HandleConektaWebhookUseCase

SCHOOL_ID = uuid4()
PLAN_ID = uuid4()


def _order_paid_event(event_id="evt_1", order_id="ord_1"):
    return {
        "id": event_id,
        "type": "order.paid",
        "data": {"object": {"id": order_id, "payment_status": "paid"}},
    }


def test_skips_processing_when_event_already_recorded():
    repo = AsyncMock()
    repo.record_webhook_event.return_value = False  # ya existía

    asyncio.run(HandleConektaWebhookUseCase(repo).execute(_order_paid_event()))

    repo.mark_status_by_order_id.assert_not_awaited()
    repo.mark_webhook_processed.assert_not_awaited()


def test_order_paid_updates_payment_and_upgrades_license():
    repo = AsyncMock()
    repo.record_webhook_event.return_value = True
    repo.mark_status_by_order_id.return_value = {"id": uuid4(), "school_id": SCHOOL_ID, "plan_id": PLAN_ID}
    repo.get_plan.return_value = {"license_tier": "premium", "billing_period": "monthly"}

    asyncio.run(HandleConektaWebhookUseCase(repo).execute(_order_paid_event()))

    _, kwargs = repo.mark_status_by_order_id.call_args
    assert kwargs["status"] == "paid"
    repo.upgrade_school_license.assert_awaited_once()
    _, upgrade_kwargs = repo.upgrade_school_license.call_args
    assert upgrade_kwargs["license_tier"] == "premium"
    repo.mark_webhook_processed.assert_awaited_once_with("evt_1")


def test_event_without_id_is_ignored():
    repo = AsyncMock()

    asyncio.run(HandleConektaWebhookUseCase(repo).execute({"type": "order.paid", "data": {}}))

    repo.record_webhook_event.assert_not_awaited()


def test_irrelevant_event_type_is_recorded_but_not_applied():
    repo = AsyncMock()
    repo.record_webhook_event.return_value = True

    asyncio.run(HandleConektaWebhookUseCase(repo).execute({"id": "evt_2", "type": "customer.created", "data": {}}))

    repo.mark_status_by_order_id.assert_not_awaited()
    repo.mark_webhook_processed.assert_awaited_once_with("evt_2")


def test_failure_records_processing_error_and_reraises():
    repo = AsyncMock()
    repo.record_webhook_event.return_value = True
    repo.mark_status_by_order_id.side_effect = RuntimeError("db down")

    try:
        asyncio.run(HandleConektaWebhookUseCase(repo).execute(_order_paid_event(event_id="evt_3")))
        assert False, "debía relanzar la excepción"
    except RuntimeError:
        pass

    repo.mark_webhook_processed.assert_awaited_once()
    _, kwargs = repo.mark_webhook_processed.call_args
    assert "db down" in kwargs["error"]
