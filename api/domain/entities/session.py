from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from domain.entities.base import Entity


@dataclass(slots=True)
class ScreeningSession(Entity):
    assignment_id: UUID | None = None
    module_code: str = ""
    status: str = "IN_PROGRESS"
    responses: list[dict] = field(default_factory=list)
