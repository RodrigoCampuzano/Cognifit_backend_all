from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.entities.base import Entity


@dataclass(slots=True)
class Student(Entity):
    group_id: UUID | None = None
    full_name: str = ""
    birth_year: int | None = None
    gender: str | None = None
    is_active: bool = True
