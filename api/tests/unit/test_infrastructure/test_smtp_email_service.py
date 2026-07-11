import asyncio


def _settings_without_smtp():
    return type("S", (), {
        "smtp_host": None, "smtp_port": 587, "smtp_user": None,
        "smtp_password": None, "email_from": None,
    })()


def _settings_with_smtp():
    return type("S", (), {
        "smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "bot@example.com",
        "smtp_password": "app-password", "email_from": "bot@example.com",
    })()


def test_send_is_noop_without_smtp_host(monkeypatch):
    from infrastructure.email import smtp_email_service as module

    monkeypatch.setattr(module, "get_settings", _settings_without_smtp)
    service = module.SmtpEmailService()

    calls = []
    monkeypatch.setattr(service, "_send_sync", lambda *a, **k: calls.append((a, k)))

    asyncio.run(service.send(to="dest@example.com", subject="Hola", body="Cuerpo"))

    assert calls == []


def test_send_calls_sync_sender_when_configured(monkeypatch):
    from infrastructure.email import smtp_email_service as module

    monkeypatch.setattr(module, "get_settings", _settings_with_smtp)
    service = module.SmtpEmailService()

    calls = []
    monkeypatch.setattr(service, "_send_sync", lambda to, subject, body: calls.append((to, subject, body)))

    asyncio.run(service.send(to="dest@example.com", subject="Hola", body="Cuerpo"))

    assert calls == [("dest@example.com", "Hola", "Cuerpo")]


def test_send_swallows_exceptions_from_smtp(monkeypatch):
    """El envío es best-effort: un fallo de SMTP no debe propagar la excepción
    (no debe romper el flujo de negocio que lo dispara, ej. registrar institución)."""
    from infrastructure.email import smtp_email_service as module

    monkeypatch.setattr(module, "get_settings", _settings_with_smtp)
    service = module.SmtpEmailService()

    def _boom(*a, **k):
        raise ConnectionRefusedError("SMTP down")

    monkeypatch.setattr(service, "_send_sync", _boom)

    # No debe lanzar.
    asyncio.run(service.send(to="dest@example.com", subject="Hola", body="Cuerpo"))
