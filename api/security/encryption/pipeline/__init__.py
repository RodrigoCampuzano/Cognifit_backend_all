"""Pipeline de cifrado en reposo / descifrado en uso (patrón visto en clase).

Arquitectura (igual que el repo de referencia, endurecida para producción):

    @sensitive (marcador)  →  MetadataEngine (descubre campos)
                                     │
    PersistenceInterceptor ──┬─ prepare_for_write  → CipherPipe  (cifra)  → BD
                             └─ materialize_from_read → DecryptPipe (descifra) → app

Diferencia de endurecimiento respecto al demo del profe: el motor criptográfico
usa **AES-256-GCM** (cifrado autenticado real) en lugar del XOR de stream de ejemplo.
El scope (p. ej. la tabla) se liga como AAD, así un ciphertext de una tabla no se
puede reutilizar en otra.
"""
from __future__ import annotations

from security.encryption.pipeline.decorators import sensitive
from security.encryption.pipeline.interceptor import PersistenceInterceptor
from security.encryption.pipeline.key_provider import KeyProvider, LocalKeyProvider
from security.encryption.pipeline.metadata_engine import MetadataEngine
from security.encryption.pipeline.pipes.cipher_pipe import CipherPipe
from security.encryption.pipeline.pipes.decrypt_pipe import DecryptPipe

__all__ = [
    "sensitive",
    "MetadataEngine",
    "KeyProvider",
    "LocalKeyProvider",
    "CipherPipe",
    "DecryptPipe",
    "PersistenceInterceptor",
    "build_persistence_interceptor",
]

# Singletons del proceso (stateless salvo cachés internas).
_metadata_engine = MetadataEngine()


def build_persistence_interceptor() -> PersistenceInterceptor:
    """Arma el interceptor con la clave maestra de la configuración."""
    from config.settings import get_settings  # lazy: evita acoplar el import a pydantic

    settings = get_settings()
    master_key = settings.field_encryption_key or settings.db_encryption_key
    provider = LocalKeyProvider(master_key=master_key, require_strong=settings.is_production)
    return PersistenceInterceptor(
        metadata_engine=_metadata_engine,
        cipher_pipe=CipherPipe(_metadata_engine, provider),
        decrypt_pipe=DecryptPipe(_metadata_engine, provider),
    )
