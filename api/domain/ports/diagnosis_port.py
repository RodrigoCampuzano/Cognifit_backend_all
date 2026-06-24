from __future__ import annotations

from typing import Protocol


class DiagnosisPort(Protocol):
    """Puerto hacia el Diagnosis Service (modelos PLN+ML entrenados, puerto 8001)."""

    async def diagnose(self, payload: dict) -> dict: ...
    async def health(self) -> dict: ...
