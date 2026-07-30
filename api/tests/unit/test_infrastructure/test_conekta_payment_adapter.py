"""ConektaPaymentAdapter: firma de webhook y aplanado de la respuesta de
/orders. No golpea la red — ConektaClient se reemplaza por un doble simple."""
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from infrastructure.conekta.conekta_payment_adapter import ConektaPaymentAdapter, _normalize_order

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def _sign(body: bytes) -> str:
    signature = _PRIVATE_KEY.sign(body, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def _settings(*, webhook_public_key=_PUBLIC_PEM):
    return type("S", (), {"conekta_webhook_public_key": webhook_public_key})()


def test_verify_webhook_signature_accepts_valid_rsa_signature():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    body = b'{"id": "evt_1", "type": "order.paid"}'
    valid_digest = _sign(body)

    assert adapter.verify_webhook_signature(payload=body, signature_header=valid_digest) is True


def test_verify_webhook_signature_rejects_tampered_body():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    body = b'{"id": "evt_1", "type": "order.paid"}'
    digest_for_other_body = _sign(b"otro body")

    assert adapter.verify_webhook_signature(payload=body, signature_header=digest_for_other_body) is False


def test_verify_webhook_signature_rejects_invalid_base64():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    assert adapter.verify_webhook_signature(payload=b"{}", signature_header="no-es-base64!!") is False


def test_verify_webhook_signature_rejects_missing_header():
    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings()

    assert adapter.verify_webhook_signature(payload=b"{}", signature_header=None) is False


def test_verify_webhook_signature_without_public_key_raises():
    from domain.exceptions.payment_exception import PaymentGatewayNotConfigured

    adapter = ConektaPaymentAdapter(client=object())
    adapter.settings = _settings(webhook_public_key=None)

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


def test_normalize_order_extracts_spei_clabe():
    order = {
        "id": "ord_789",
        "payment_status": "pending_payment",
        "charges": {
            "data": [
                {
                    "status": "pending_payment",
                    "payment_method": {
                        "type": "spei",
                        "clabe": "646180157042875763",
                        "bank": "STP",
                        "expires_at": 1735689600,
                    },
                }
            ]
        },
    }

    result = _normalize_order(order)

    assert result["spei"]["clabe"] == "646180157042875763"
    assert result["spei"]["bank"] == "STP"


def test_normalize_order_without_cash_charge_has_no_cash_key():
    order = {
        "id": "ord_456",
        "payment_status": "paid",
        "charges": {"data": [{"status": "paid", "payment_method": {"type": "card"}}]},
    }

    result = _normalize_order(order)

    assert result["status"] == "paid"
    assert "cash" not in result
    assert "spei" not in result
