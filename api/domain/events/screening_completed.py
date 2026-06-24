from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.events.base_event import DomainEvent


@dataclass(frozen=True, slots=True)
class ScreeningCompleted(DomainEvent):
    student_id: UUID | None = None
    session_id: UUID | None = None
    risk_probability: float = 0.0
