from __future__ import annotations

import base64
import logging

import httpx

from config.settings import get_settings
from domain.exceptions.payment_exception import ConektaApiError, PaymentGatewayNotConfigured

logger = logging.getLogger(__name__)


class ConektaClient:
    """Cliente HTTP crudo de la API REST de Conekta (https://api.conekta.io).

    Mismo patrón que infrastructure/pln/diagnosis_client.py: un único
    AsyncClient perezoso (creado dentro del event loop que lo usa, no en
    __init__) reutilizado entre llamadas.

    No conoce reglas de negocio (planes, escuelas, licencias) — solo sabe
    hablar el protocolo HTTP de Conekta. Eso vive en conekta_payment_adapter.py.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self.settings.conekta_private_key:
            raise PaymentGatewayNotConfigured("CONEKTA_PRIVATE_KEY no está configurada en este entorno")
        if self._client is None or self._client.is_closed:
            auth = base64.b64encode(f"{self.settings.conekta_private_key}:".encode()).decode()
            self._client = httpx.AsyncClient(
                base_url=self.settings.conekta_base_url,
                timeout=20.0,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Accept": f"application/vnd.conekta-v{self.settings.conekta_api_version}+json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def _request(self, method: str, path: str, *, json: dict | None = None, idempotency_key: str | None = None) -> dict:
        client = self._get_client()
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        try:
            response = await client.request(method, path, json=json, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("Conekta %s %s falló: %r", method, path, exc)
            raise ConektaApiError(f"No se pudo contactar a Conekta: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            logger.warning("Conekta %s %s -> %s: %s", method, path, response.status_code, detail)
            raise ConektaApiError(detail)
        return response.json()

    async def create_customer(self, *, email: str, name: str) -> dict:
        return await self._request("POST", "/customers", json={"name": name, "email": email})

    async def create_order(self, payload: dict, *, idempotency_key: str) -> dict:
        return await self._request("POST", "/orders", json=payload, idempotency_key=idempotency_key)

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"/orders/{order_id}")


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        details = body.get("details") or []
        if details:
            return "; ".join(d.get("message", str(d)) for d in details)
        return body.get("message") or body.get("error") or response.text
    except ValueError:
        return response.text
