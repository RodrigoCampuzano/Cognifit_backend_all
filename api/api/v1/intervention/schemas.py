from __future__ import annotations

from pydantic import BaseModel, Field


class SessionRecordSchema(BaseModel):
    exercise_id: str
    accuracy: float = Field(..., ge=0, le=1)


class NextExerciseRequest(BaseModel):
    current_route: list[str] = Field(..., description="exercise_ids de la ruta activa, en orden")
    session_history: list[SessionRecordSchema] = Field(default_factory=list)
