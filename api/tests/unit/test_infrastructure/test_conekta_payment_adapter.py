"""ConektaPaymentAdapter: firma de webhook y aplanado de la respuesta de
/orders. No golpea la red — ConektaClient se reemplaza por un doble simple."""
import hashlib
import hmac

from infrastructure.conekta.conekta_payment_adapter import ConektaPaymentAdapter, _normalize_order


def _settings(*, webhook_secret="shh"):
    return type("S", (), {"conekta_webhook_secret": webhook_secret})()


def test_verify_webhook_signature_accepts_valid_hmac():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    body = b'{"id": "evt_1", "type": "order.paid"}'
    valid_signature = hmac.new(b"shh", body, hashlib.sha256).hexdigest()

    assert adapter.verify_webhook_signature(payload=body, signature_header=valid_signature) is True


def test_verify_webhook_signature_rejects_tampered_body():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    body = b'{"id": "evt_1", "type": "order.paid"}'
    signature_for_other_body = hmac.new(b"shh", b"otro body", hashlib.sha256).hexdigest()

    assert adapter.verify_webhook_signature(payload=body, signature_header=signature_for_other_body) is False


def test_verify_webhook_signature_rejects_missing_header():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    assert adapter.verify_webhook_signature(payload=b"{}", signature_header=None) is False


def test_verify_webhook_signature_without_secret_raises():
    from domain.exceptions.payment_exception import PaymentGatewayNotConfigured

    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings(webhook_secret=None)

    try:
        adapter.verify_webhook_signature(payload=b"{}", signature_header="x")
        assert False, "debía lanzar PaymentGatewayNotConfigured"
    except PaymentGatewayNotConfigured:
        pass


def test_normalize_order_extracts_cash_reference():
    order = {
        "id": "ord_123",
        "payment_status": "pending_payment",
        "charges": {
            "data": [
                {
                    "status": "pending_payment",
                    "payment_method": {
                        "type": "cash",
                        "reference": "93000001234567",
                        "barcode_url": "https://cdn.conekta.io/barcode.png",
                        "expires_at": 1735689600,
                    },
                }
            ]
        },
    }

    result = _normalize_order(order)

    assert result["id"] == "ord_123"
    assert result["status"] == "pending_payment"
    assert result["cash"]["reference"] == "93000001234567"
    assert result["cash"]["barcode_url"].startswith("https://")


def test_normalize_order_without_cash_charge_has_no_cash_key():
    order = {
        "id": "ord_456",
        "payment_status": "paid",
        "charges": {"data": [{"status": "paid", "payment_method": {"type": "card"}}]},
    }

    result = _normalize_order(order)

    assert result["status"] == "paid"
    assert "cash" not in result
