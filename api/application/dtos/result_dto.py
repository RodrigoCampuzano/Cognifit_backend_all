from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnosisDto(BaseModel):
    subtype: str
    severity: str | None
    risk_probability: float = Field(ge=0, le=1)
    risk_level: str
    main_error_codes: list[str]
    feature_vector_28: list[float] = Field(min_length=28, max_length=28)
    recommended_route: list[str]
    recommendation_reason: str
