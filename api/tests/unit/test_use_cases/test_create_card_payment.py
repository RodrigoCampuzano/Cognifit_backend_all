"""CreateCardPaymentUseCase: orquesta repo (persistencia) + gateway (Conekta)
sin tocar red ni base real — ambos se reemplazan por AsyncMock."""
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from application.use_cases.payments.create_card_payment import CreateCardPaymentUseCase

PLAN = {
    "id": uuid4(),
    "code": "premium_mensual",
    "name": "Premium mensual",
    "license_tier": "premium",
    "price_cents": 49900,
    "currency": "MXN",
    "billing_period": "monthly",
}


def _repo(*, existing_customer_id=None):
    repo = AsyncMock()
    repo.get_plan.return_value = PLAN
    repo.get_customer_id.return_value = existing_customer_id
    repo.create_pending_payment.return_value = {"id": uuid4(), "idempotency_key": "idem-1"}
    repo.attach_conekta_order.side_effect = lambda payment_id, **kw: {"id": payment_id, **kw}
    return repo


def _gateway(*, order_status="paid"):
    gateway = AsyncMock()
    gateway.create_customer.return_value = "cus_new"
    gateway.create_card_order.return_value = {"id": "ord_1", "status": order_status, "raw": {"id": "ord_1"}}
    return gateway


def test_creates_conekta_customer_when_school_has_none():
    repo = _repo(existing_customer_id=None)
    gateway = _gateway()

    asyncio.run(CreateCardPaymentUseCase(repo, gateway).execute(
        school_id=uuid4(), plan_id=PLAN["id"], created_by_user_id=uuid4(),
        admin_email="director@escuela.edu", admin_name="director@escuela.edu", token_id="tok_xxx",
    ))

    gateway.create_customer.assert_awaited_once()
    repo.save_customer_id.assert_awaited_once()


def test_reuses_existing_conekta_customer():
    repo = _repo(existing_customer_id="cus_existing")
    gateway = _gateway()

    asyncio.run(CreateCardPaymentUseCase(repo, gateway).execute(
        school_id=uuid4(), plan_id=PLAN["id"], created_by_user_id=uuid4(),
        admin_email="director@escuela.edu", admin_name="director@escuela.edu", token_id="tok_xxx",
    ))

    gateway.create_customer.assert_not_awaited()
    args, kwargs = gateway.create_card_order.call_args
    assert kwargs["customer_id"] == "cus_existing"


def test_paid_order_upgrades_school_license():
    repo = _repo(existing_customer_id="cus_1")
    gateway = _gateway(order_status="paid")

    asyncio.run(CreateCardPaymentUseCase(repo, gateway).execute(
        school_id=uuid4(), plan_id=PLAN["id"], created_by_user_id=uuid4(),
        admin_email="a@b.com", admin_name="a@b.com", token_id="tok_xxx",
    ))

    repo.upgrade_school_license.assert_awaited_once()
    _, kwargs = repo.upgrade_school_license.call_args
    assert kwargs["license_tier"] == "premium"


def test_declined_order_does_not_upgrade_license():
    repo = _repo(existing_customer_id="cus_1")
    gateway = _gateway(order_status="declined")

    asyncio.run(CreateCardPaymentUseCase(repo, gateway).execute(
        school_id=uuid4(), plan_id=PLAN["id"], created_by_user_id=uuid4(),
        admin_email="a@b.com", admin_name="a@b.com", token_id="tok_xxx",
    ))

    repo.upgrade_school_license.assert_not_awaited()
    _, kwargs = repo.attach_conekta_order.call_args
    assert kwargs["status"] == "failed"


def test_uses_idempotency_key_from_pending_payment_across_gateway_call():
    repo = _repo(existing_customer_id="cus_1")
    gateway = _gateway()

    asyncio.run(CreateCardPaymentUseCase(repo, gateway).execute(
        school_id=uuid4(), plan_id=PLAN["id"], created_by_user_id=uuid4(),
        admin_email="a@b.com", admin_name="a@b.com", token_id="tok_xxx",
    ))

    pending_key = repo.create_pending_payment.call_args.kwargs["idempotency_key"]
    order_key = gateway.create_card_order.call_args.kwargs["idempotency_key"]
    assert pending_key == order_key
