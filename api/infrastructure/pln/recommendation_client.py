from __future__ import annotations

import logging

import httpx

from infrastructure.pln.errors import PlnServiceError

logger = logging.getLogger(__name__)


class RecommendationServiceClient:
    """Cliente HTTP del Recommendation Service (8002)."""

    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def recommend(self, payload: dict) -> dict:
        return await self._post("/recommend", payload)

    async def next_exercise(self, payload: dict) -> dict:
        return await self._post("/next-exercise", payload)

    async def get_exercise(self, exercise_id: str) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            try:
                resp = await client.get(f"/exercises/{exercise_id}")
            except httpx.HTTPError as exc:
                raise PlnServiceError("recommendation", repr(exc)) from exc
            if resp.status_code == 404:
                raise PlnServiceError("recommendation", f"ejercicio '{exercise_id}' no encontrado", 404)
            if resp.status_code != 200:
                raise PlnServiceError("recommendation", resp.text, resp.status_code)
            return resp.json()

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            try:
                resp = await client.post(path, json=payload)
            except httpx.HTTPError as exc:
                raise PlnServiceError("recommendation", repr(exc)) from exc
            if resp.status_code == 200:
                return resp.json()
            raise PlnServiceError("recommendation", resp.text, resp.status_code)

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.get("/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            return {"status": "down", "service": "recommendation", "error": str(exc)}
