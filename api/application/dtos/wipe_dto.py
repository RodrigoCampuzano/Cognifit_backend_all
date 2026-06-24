from __future__ import annotations

from pydantic import BaseModel, Field


class WipeDto(BaseModel):
    user_id: str
    device_id: str | None = None
    reason: str = Field(min_length=3, max_length=200)
