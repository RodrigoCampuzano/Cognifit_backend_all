from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID

from application.dtos.session_dto import ResponseDto, StartSessionDto


class TeacherAnswer(BaseModel):
    item_code: str
    value: str | float = Field(description="Nunca=0, A veces=0.5, Frecuente=1")


class TeacherScreeningRequest(BaseModel):
    student_id: UUID
    # No hay un tamaño fijo: PRODISLEX define un protocolo distinto por ciclo
    # (1er, 2º y 3er ciclo de primaria) y la cantidad de ítems activos difiere
    # entre ellos (ver migración 023_prodislex_por_ciclo.sql). La validación
    # real de que cada ítem del ciclo del alumno tenga respuesta ocurre en
    # ScreeningService.calculate_teacher_score, que compara contra los ítems
    # vigentes para su grado — no contra un conteo fijo aquí.
    answers: list[TeacherAnswer] = Field(min_length=1)


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


class LabelDiagnosisRequest(BaseModel):
    confirmed_subtype: str = Field(description="PHONOLOGICAL | VISUAL_SURFACE | MIXED | NO_DYSLEXIA | FLUENCY | COMPREHENSION | RISK_ONLY")
    confirmed_severity: str = Field(description="MILD | MODERATE | SEVERE | NONE")
    confirmed_risk_level: str = Field(pattern=r"^(LOW|MEDIUM|HIGH)$")
    notes: str | None = None
