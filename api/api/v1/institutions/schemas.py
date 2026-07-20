from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterInstitutionRequest(BaseModel):
    school_name: str = Field(..., min_length=2)
    cct: str | None = Field(default=None, description="Clave de Centro de Trabajo (SEP)")
    state: str = "Chiapas"
    municipality: str | None = None
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)


class InstitutionResponse(BaseModel):
    id: UUID
    name: str
    cct: str | None
    state: str
    municipality: str | None
    is_active: bool
    created_at: datetime
    approved_at: datetime | None


class RejectInstitutionRequest(BaseModel):
    # Opcional pero acotado: el motivo viaja al correo del solicitante, así que
    # conviene un texto breve y no un campo libre sin límite.
    reason: str | None = Field(default=None, max_length=500)
