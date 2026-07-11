from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID


class CreateGroupRequest(BaseModel):
    grade: int = Field(ge=1, le=6)                      # 1° a 6° de primaria
    group_label: str = Field(min_length=1, max_length=16)   # "A", "B", "9-D"
    school_year: str = Field(default="2025-2026", min_length=4, max_length=16)


class GroupResponse(BaseModel):
    id: UUID
    grade: int
    group_label: str
    school_year: str
    is_active: bool = True
    student_count: int = 0
