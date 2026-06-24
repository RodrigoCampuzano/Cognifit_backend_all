from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID


class StartSessionDto(BaseModel):
    assignment_id: UUID
    module_code: str = Field(min_length=3, max_length=64)
    device_id: str | None = Field(default=None, max_length=120)
    app_version: str | None = Field(default=None, max_length=40)


class ResponseDto(BaseModel):
    item_id: UUID
    raw_response: str | None = Field(default=None, max_length=2000)
    response_time_ms: int | None = Field(default=None, ge=0, le=300000)
    capture_modality: str | None = Field(default=None, max_length=40)
    response_audio_url: str | None = Field(default=None, max_length=2000)
    stt_confidence: float | None = Field(default=None, ge=0, le=1)
