from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ResultRepository(Protocol):
    async def save_diagnosis(self, session_id: UUID, result: dict) -> dict: ...
    async def get_latest_risk(self, student_id: UUID) -> dict | None: ...
