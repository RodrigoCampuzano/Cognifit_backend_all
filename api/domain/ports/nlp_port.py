from __future__ import annotations

from typing import Protocol


class NlpPort(Protocol):
    def analyze_response(self, expected: str, produced: str, item_kind: str | None = None) -> dict: ...
    def build_feature_vector(self, analyses: list[dict], grade: int, teacher_score: float) -> list[float]: ...
