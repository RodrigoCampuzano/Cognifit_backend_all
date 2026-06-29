"""Contrato de los filtros del pipeline (PIPE del pizarrón)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict


class PipeContext(TypedDict, total=False):
    scope: str  # p. ej. nombre de tabla; lo usa el KeyProvider y como AAD


class PipelineFilter(ABC):
    @abstractmethod
    def execute(self, entity: object, context: PipeContext) -> object:
        raise NotImplementedError
