from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @classmethod
    def from_probability(cls, probability: float) -> "RiskLevel":
        if probability >= 0.66:
            return cls.HIGH
        if probability >= 0.31:
            return cls.MEDIUM
        return cls.LOW
