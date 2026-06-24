from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Score:
    value: float

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValueError("Score must be between 0 and 100")

    @property
    def normalized(self) -> float:
        return self.value / 100
