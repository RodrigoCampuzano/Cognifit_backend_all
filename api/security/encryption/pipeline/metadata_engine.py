"""Descubre y cachea qué campos de cada entidad están marcados como sensibles."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from threading import RLock


class MetadataEngine:
    def __init__(self) -> None:
        self._cache: dict[type[object], tuple[str, ...]] = {}
        self._lock = RLock()  # acceso concurrente desde repositorios

    def get_sensitive_fields(self, entity_type: type[object]) -> tuple[str, ...]:
        with self._lock:
            cached = self._cache.get(entity_type)
            if cached is not None:
                return cached
            discovered: tuple[str, ...] = ()
            if is_dataclass(entity_type):
                discovered = tuple(
                    f.name for f in fields(entity_type) if f.metadata.get("sensitive", False) is True
                )
            self._cache[entity_type] = discovered  # memoiza incluso vacío
            return discovered

    def has_sensitive_fields(self, entity_type: type[object]) -> bool:
        return bool(self.get_sensitive_fields(entity_type))
