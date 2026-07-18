from __future__ import annotations

import asyncio
import logging

import httpx

from infrastructure.pln.errors import PlnServiceError

logger = logging.getLogger(__name__)


class DiagnosisServiceClient:
    """Cliente HTTP del Diagnosis Service (8001). Reintenta ante 503 (modelos
    cargando) y lanza PlnServiceError si se agotan los reintentos / hay timeout.

    Mantiene un único AsyncClient reutilizable (keep-alive): antes se abría una
    conexión TCP+TLS nueva en cada llamada, y como el cliente es un singleton
    (@lru_cache en dependencies/services.py) ese costo se pagaba en cada
    diagnóstico sin necesidad.
    """

    def __init__(self, base_url: str, *, timeout: float = 10.0, retries: int = 1) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        # Perezoso: el cliente debe crearse dentro del event loop que lo usa,
        # no en el __init__ (que corre al resolver la dependencia cacheada).
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def diagnose(self, payload: dict) -> dict:
        last_detail = "sin respuesta"
        client = self._get_client()
        for attempt in range(self.retries + 1):
            try:
                resp = await client.post("/diagnose", json=payload)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_detail = f"conexión/timeout: {exc!r}"
                logger.warning("Diagnosis Service intento %s falló: %s", attempt, last_detail)
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 503:
                    last_detail = "modelos no cargados (503)"
                    logger.warning("Diagnosis Service 503, reintentando (intento %s)", attempt)
                else:
                    raise PlnServiceError("diagnosis", resp.text, resp.status_code)
            if attempt < self.retries:
                await asyncio.sleep(1.0)
        raise PlnServiceError("diagnosis", last_detail, 503)

    async def health(self) -> dict:
        try:
            resp = await self._get_client().get("/health")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            return {"status": "down", "service": "diagnosis", "error": str(exc)}
