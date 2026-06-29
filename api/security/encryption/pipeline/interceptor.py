"""Interceptor de persistencia: el punto único que el repositorio invoca para
cifrar antes de escribir y descifrar después de leer."""
from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

from security.encryption.pipeline.metadata_engine import MetadataEngine
from security.encryption.pipeline.pipes.cipher_pipe import CipherPipe
from security.encryption.pipeline.pipes.decrypt_pipe import DecryptPipe

TEntity = TypeVar("TEntity")


class PersistenceInterceptor:
    def __init__(self, metadata_engine: MetadataEngine, cipher_pipe: CipherPipe, decrypt_pipe: DecryptPipe) -> None:
        self._metadata = metadata_engine
        self._cipher = cipher_pipe
        self._decrypt = decrypt_pipe

    def prepare_for_write(self, entity: TEntity, scope: str | None = None) -> TEntity:
        """Devuelve una COPIA con los campos sensibles cifrados (la BD recibe esto)."""
        if not self._metadata.has_sensitive_fields(type(entity)):
            return entity
        materialized = deepcopy(entity)  # no muta el objeto de dominio del caller
        return self._cipher.execute(materialized, {"scope": scope or type(entity).__name__})

    def materialize_from_read(self, entity: TEntity, scope: str | None = None) -> TEntity:
        """Devuelve una COPIA con los campos sensibles descifrados (la app recibe esto)."""
        if not self._metadata.has_sensitive_fields(type(entity)):
            return entity
        materialized = deepcopy(entity)
        return self._decrypt.execute(materialized, {"scope": scope or type(entity).__name__})
