"""Provee la clave por scope. Endurecido: deriva una clave AES-256 por scope
desde una clave maestra, y exige clave fuerte en producción."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

_INSECURE_DEFAULT = "local-dev-master-key"


class KeyProvider(ABC):
    @abstractmethod
    def get_key(self, scope: str) -> bytes:
        raise NotImplementedError


class LocalKeyProvider(KeyProvider):
    """Deriva una clave de 32 bytes por scope: SHA-256(master || ':' || scope).

    En producción rechaza claves vacías o el default de desarrollo (HU-BD-11).
    En un entorno real, la master key vendría de un KMS/secret manager.
    """

    def __init__(self, master_key: str | None, *, require_strong: bool = False) -> None:
        if not master_key or master_key == _INSECURE_DEFAULT:
            if require_strong:
                raise RuntimeError(
                    "Clave de cifrado ausente o insegura. Configura FIELD_ENCRYPTION_KEY "
                    "(o DB_ENCRYPTION_KEY) en producción."
                )
            master_key = master_key or _INSECURE_DEFAULT
        self._master = master_key.encode("utf-8")
        self._cache: dict[str, bytes] = {}

    def get_key(self, scope: str) -> bytes:
        key = self._cache.get(scope)
        if key is None:
            key = hashlib.sha256(self._master + b":" + scope.encode("utf-8")).digest()
            self._cache[scope] = key
        return key
