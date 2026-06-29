"""Decrypt Filter + DecryptPipe: descifra los campos sensibles al leer de la BD."""
from __future__ import annotations

from typing import TypeVar, cast

from security.encryption.pipeline.key_provider import KeyProvider
from security.encryption.pipeline.metadata_engine import MetadataEngine
from security.encryption.pipeline.pipes.base import PipeContext, PipelineFilter
from security.encryption.pipeline.pipes import crypto

TEntity = TypeVar("TEntity")


class AesGcmDecryptFilter(PipelineFilter):
    def __init__(self, metadata_engine: MetadataEngine, key_provider: KeyProvider) -> None:
        self._metadata = metadata_engine
        self._keys = key_provider

    def execute(self, entity: object, context: PipeContext) -> object:
        sensitive_fields = self._metadata.get_sensitive_fields(type(entity))
        if not sensitive_fields:
            return entity
        scope = context.get("scope", type(entity).__name__)
        key = self._keys.get_key(scope)
        for name in sensitive_fields:
            value = getattr(entity, name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"El campo sensible '{name}' debe ser str o None.")
            if not crypto.is_encrypted(value):  # resiliente a valores en claro
                continue
            setattr(entity, name, crypto.decrypt_value(value, key, scope=scope))
        return entity


class DecryptPipe:
    def __init__(self, metadata_engine: MetadataEngine, key_provider: KeyProvider, filters: list[PipelineFilter] | None = None) -> None:
        self._filters = filters or [AesGcmDecryptFilter(metadata_engine, key_provider)]

    def execute(self, entity: TEntity, context: PipeContext | None = None) -> TEntity:
        current: object = entity
        for filter_ in self._filters:
            current = filter_.execute(current, context or {})
        return cast(TEntity, current)
