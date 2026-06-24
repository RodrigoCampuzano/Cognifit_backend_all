from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.events.base_event import DomainEvent


@dataclass(frozen=True, slots=True)
class WipeTriggered(DomainEvent):
    user_id: UUID | None = None
    device_id: str | None = None
    reason: str = "security_policy"
