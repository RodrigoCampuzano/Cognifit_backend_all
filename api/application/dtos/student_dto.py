from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class StudentDto(BaseModel):
    id: UUID
    group_id: UUID
    full_name: str
    birth_year: int | None = None
    gender: str | None = None
    is_active: bool = True


class RegisterStudentDto(BaseModel):
    group_id: UUID
    full_name: str = Field(min_length=1, max_length=180)
    birth_year: int | None = Field(default=None, ge=2008, le=2022)
    gender: str | None = Field(default=None, max_length=16)
    guardian_name: str | None = Field(default=None, max_length=180)
    # EmailStr y no str: era el único campo de correo del proyecto que no lo
    # usaba, así que un correo de tutor mal escrito ("sin-arroba") pasaba la
    # validación y solo fallaba, en silencio, al intentar notificarle.
    guardian_email: EmailStr | None = Field(default=None, max_length=255)
