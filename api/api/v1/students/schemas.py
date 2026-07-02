from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID


class RegisterStudentRequest(BaseModel):
    group_id: UUID
    full_name: str = Field(min_length=1, max_length=180)
    birth_year: int | None = Field(default=None, ge=2008, le=2022)
    gender: str | None = Field(default=None, max_length=16)


class StudentResponse(BaseModel):
    id: UUID
    group_id: UUID
    full_name: str
    birth_year: int | None = None
    gender: str | None = None
    is_active: bool = True


class LinkedStudentResponse(BaseModel):
    id: UUID
    full_name: str
    group_id: UUID
