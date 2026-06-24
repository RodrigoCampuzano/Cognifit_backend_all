from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID

from application.dtos.session_dto import ResponseDto, StartSessionDto


class TeacherAnswer(BaseModel):
    item_code: str
    value: str | float = Field(description="Nunca=0, A veces=0.5, Frecuente=1")


class TeacherScreeningRequest(BaseModel):
    student_id: UUID
    answers: list[TeacherAnswer] = Field(min_length=8, max_length=8)


class TeacherScreeningResponse(BaseModel):
    id: UUID
    student_id: UUID
    teacher_id: UUID
    score: float
    battery_mode: str
    answers: list[dict] | dict
    risk_flags: list[dict] | dict
    enabled_module_codes: list[str]


class CreateAssignmentsRequest(BaseModel):
    student_id: UUID
    teacher_score: float = Field(ge=0, le=100)
    risk_flags: list[dict] = Field(default_factory=list)


class StartSessionRequest(StartSessionDto):
    raw_client_payload: dict = Field(default_factory=dict)


class SubmitResponsesRequest(BaseModel):
    responses: list[ResponseDto] = Field(min_length=1, max_length=200)
