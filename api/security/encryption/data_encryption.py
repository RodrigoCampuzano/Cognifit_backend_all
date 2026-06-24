from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from config.settings import get_settings


class DataEncryption:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.field_encryption_key
        self._fernet = Fernet(key.encode()) if key else None

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, value: str) -> str:
        if not self._fernet:
            raise RuntimeError("FIELD_ENCRYPTION_KEY is not configured")
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not self._fernet:
            raise RuntimeError("FIELD_ENCRYPTION_KEY is not configured")
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted value") from exc
