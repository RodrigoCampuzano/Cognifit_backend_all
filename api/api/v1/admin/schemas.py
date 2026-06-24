from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

ROLES = Literal["ADMIN", "SPECIALIST", "TEACHER", "PARENT", "STUDENT"]


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: ROLES


class UpdateUserRequest(BaseModel):
    role: ROLES | None = None
    is_active: bool | None = None


class ActivateModelRequest(BaseModel):
    version_tag: str = Field(..., min_length=1)
