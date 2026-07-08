from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.events.base_event import DomainEvent


@dataclass(frozen=True, slots=True)
class ProgressEvaluated(DomainEvent):
    student_id: UUID | None = None
    teacher_id: UUID | None = None
    action: str = "none"  # "stagnation" | "level_up" | "none"
    urgency: str = "MEDIUM"
    message: str = ""
    suggested_action: str = ""
