from __future__ import annotations

import asyncio
import logging

import httpx

from infrastructure.pln.errors import PlnServiceError

logger = logging.getLogger(__name__)


class DiagnosisServiceClient:
    """Cliente HTTP del Diagnosis Service (8001). Reintenta ante 503 (modelos
    cargando) y lanza PlnServiceError si se agotan los reintentos / hay timeout."""

    def __init__(self, base_url: str, *, timeout: float = 10.0, retries: int = 1) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)

    async def diagnose(self, payload: dict) -> dict:
        last_detail = "sin respuesta"
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
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
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.get("/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            return {"status": "down", "service": "diagnosis", "error": str(exc)}
