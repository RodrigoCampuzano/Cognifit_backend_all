from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(slots=True)
class Entity:
    id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
