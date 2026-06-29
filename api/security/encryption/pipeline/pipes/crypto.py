"""Motor criptográfico endurecido: AES-256-GCM (cifrado autenticado).

Formato del token:  enc::v1::base64url(nonce[12] || ciphertext+tag)
El `scope` se liga como AAD para que un ciphertext no sea válido en otra tabla.
"""
from __future__ import annotations

import base64

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "enc::v1::"
_NONCE_BYTES = 12


def is_encrypted(value: str) -> bool:
    return value.startswith("enc::")


def encrypt_value(plaintext: str, key: bytes, *, scope: str) -> str:
    import os

    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), scope.encode("utf-8"))
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")
    return f"{PREFIX}{token}"


def decrypt_value(token: str, key: bytes, *, scope: str) -> str:
    if not token.startswith(PREFIX):
        raise ValueError("Formato de token no soportado.")
    decoded = base64.urlsafe_b64decode(token.removeprefix(PREFIX).encode("utf-8"))
    if len(decoded) < _NONCE_BYTES:
        raise ValueError("Payload cifrado sin nonce.")
    nonce, ciphertext = decoded[:_NONCE_BYTES], decoded[_NONCE_BYTES:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, scope.encode("utf-8")).decode("utf-8")
    except InvalidTag as exc:  # clave incorrecta o dato manipulado
        raise ValueError("Ciphertext inválido para la clave/scope actuales.") from exc
