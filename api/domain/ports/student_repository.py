from __future__ import annotations

from typing import Protocol
from uuid import UUID


class StudentRepository(Protocol):
    async def list_students(self, group_id: UUID | None = None) -> list[dict]: ...
    async def get_student(self, student_id: UUID) -> dict | None: ...
    async def register_student(self, data: dict) -> dict: ...
