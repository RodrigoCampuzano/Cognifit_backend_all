from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(pattern="^(ADMIN|SPECIALIST|TEACHER|PARENT|STUDENT)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: str | None = Field(default=None, max_length=200)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class CurrentUserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool = True

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: str | UUID) -> str:
        return str(value)
