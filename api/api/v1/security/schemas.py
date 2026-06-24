from __future__ import annotations

from pydantic import BaseModel, Field


class AuditEventRequest(BaseModel):
    action: str = Field(min_length=3, max_length=120)
    target_table: str | None = Field(default=None, max_length=120)
    target_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class TriggerWipeRequest(BaseModel):
    user_id: str
    device_id: str | None = None
    reason: str = Field(min_length=3, max_length=200)
