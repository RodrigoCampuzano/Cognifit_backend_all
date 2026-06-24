from __future__ import annotations

from typing import Protocol
from uuid import UUID


class SessionRepository(Protocol):
    async def get_battery_catalog(self) -> list[dict]: ...
    async def create_assignments(self, student_id: UUID, module_codes: list[str], teacher_id: UUID) -> list[dict]: ...
    async def save_response(self, data: dict) -> dict: ...
