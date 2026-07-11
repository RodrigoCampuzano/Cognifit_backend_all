from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from config.settings import get_settings


class JWTService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_access_token(
        self, *, user_id: UUID | str, email: str, role: str, institution_id: UUID | str | None = None
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "institution_id": str(institution_id) if institution_id else None,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": now + timedelta(minutes=self.settings.access_token_expire_minutes),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def create_refresh_token(self, *, user_id: UUID | str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": now + timedelta(days=self.settings.refresh_token_expire_days),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def decode(self, token: str, expected_type: str | None = None) -> dict:
        payload = jwt.decode(token, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
        if expected_type and payload.get("type") != expected_type:
            raise jwt.InvalidTokenError("Invalid token type")
        return payload
