from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SmtpEmailService:
    """Envío de correo vía SMTP estándar (stdlib, sin dependencias nuevas).
    Se degrada a no-op si SMTP_HOST no está configurado — mismo patrón que
    infrastructure/cache/redis_client.py con REDIS_URL, para no romper el
    flujo mientras el correo no esté configurado en el entorno."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send(self, *, to: str, subject: str, body: str) -> None:
        if not self.settings.smtp_host:
            logger.debug("SMTP no configurado — se omite el envío de correo a %s", to)
            return
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
        except Exception:
            # El envío de correo es "best effort": nunca debe romper la operación
            # de negocio (ej. registrar una institución) si el SMTP falla.
            logger.exception("Falló el envío de correo a %s", to)

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.email_from or self.settings.smtp_user
        message["To"] = to
        message.set_content(body)

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if self.settings.smtp_user and self.settings.smtp_password:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)
