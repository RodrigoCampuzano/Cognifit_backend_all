from __future__ import annotations

from dataclasses import dataclass, field

from domain.entities.base import Entity


@dataclass(slots=True)
class DiagnosisResult(Entity):
    subtype: str = "NO_DYSLEXIA"
    severity: str | None = None
    risk_probability: float = 0.0
    risk_level: str = "LOW"
    main_error_codes: list[str] = field(default_factory=list)
    recommended_route: list[str] = field(default_factory=list)
