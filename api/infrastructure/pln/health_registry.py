from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.recommendation_client import RecommendationServiceClient


class HealthRegistry:
    """Singleton: mantiene el último estado conocido de los microservicios PLN
    entre requests, evitando que cada consulta de monitoreo dependa de una
    llamada de red en vivo."""

    def __init__(self) -> None:
        self._snapshot: dict | None = None

    async def refresh(
        self, diagnosis: DiagnosisServiceClient, recommendation: RecommendationServiceClient
    ) -> dict:
        d = await diagnosis.health()
        r = await recommendation.health()
        all_ok = d.get("status") == "ok" and r.get("status") == "ok"
        self._snapshot = {
            "status": "ok" if all_ok else "degraded",
            "diagnosis": d,
            "recommendation": r,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._snapshot

    def snapshot(self) -> dict | None:
        return self._snapshot
