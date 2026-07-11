from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_by_email(self, email: str) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                SELECT u.id, u.email, u.password_hash, u.role::text AS role, u.is_active,
                       u.institution_id, COALESCE(s.is_active, TRUE) AS institution_is_active
                FROM auth.users u
                LEFT JOIN academic.schools s ON s.id = u.institution_id
                WHERE lower(u.email)=lower(:email)
                '''
            ),
            {"email": email},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_by_id(self, user_id: UUID | str) -> dict | None:
        result = await self.session.execute(
            text("SELECT id, email, role::text AS role, is_active, institution_id FROM auth.users WHERE id=:id"),
            {"id": str(user_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_user(self, *, email: str, password_hash: str, role: str, institution_id: UUID | str | None = None) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO auth.users (email, password_hash, role, institution_id)
                VALUES (:email, :password_hash, CAST(:role AS auth.user_role), :institution_id)
                RETURNING id, email, role::text AS role, is_active, institution_id, created_at
                '''
            ),
            {
                "email": email.lower(),
                "password_hash": password_hash,
                "role": role,
                "institution_id": str(institution_id) if institution_id else None,
            },
        )
        return dict(result.mappings().one())

    async def list_users(
        self, *, role: str | None = None, include_inactive: bool = False, institution_id: UUID | str | None = None
    ) -> list[dict]:
        clauses = []
        params: dict = {}
        if role:
            clauses.append("role = CAST(:role AS auth.user_role)")
            params["role"] = role
        if not include_inactive:
            clauses.append("is_active = TRUE")
        if institution_id:
            clauses.append("institution_id = :institution_id")
            params["institution_id"] = str(institution_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        result = await self.session.execute(
            text(f"SELECT id, email, role::text AS role, is_active, institution_id, created_at FROM auth.users {where} ORDER BY created_at DESC"),
            params,
        )
        return [dict(r) for r in result.mappings().all()]

    async def update_user(
        self, user_id: UUID | str, *, role: str | None = None, is_active: bool | None = None, institution_id: UUID | str | None = None
    ) -> dict | None:
        sets = []
        params: dict = {"id": str(user_id)}
        if role is not None:
            sets.append("role = CAST(:role AS auth.user_role)")
            params["role"] = role
        if is_active is not None:
            sets.append("is_active = :is_active")
            params["is_active"] = is_active
        if not sets:
            return await self.get_by_id(user_id)
        where = "WHERE id = :id"
        if institution_id is not None:
            where += " AND institution_id = :institution_id"
            params["institution_id"] = str(institution_id)
        result = await self.session.execute(
            text(f"UPDATE auth.users SET {', '.join(sets)} {where} RETURNING id, email, role::text AS role, is_active"),
            params,
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def deactivate_user(self, user_id: UUID | str, *, institution_id: UUID | str | None = None) -> dict | None:
        """Borrado lógico (HU-BK-03): nunca borrado físico. Acotado a la
        institución del solicitante — sin esto, un ADMIN podía desactivar
        cuentas de cualquier otra escuela."""
        where = "WHERE id = :id"
        params: dict = {"id": str(user_id)}
        if institution_id is not None:
            where += " AND institution_id = :institution_id"
            params["institution_id"] = str(institution_id)
        result = await self.session.execute(
            text(f"UPDATE auth.users SET is_active = FALSE {where} RETURNING id, email, role::text AS role, is_active"),
            params,
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def store_refresh_token(self, *, user_id: UUID | str, token: str, device_info: str | None, ip_address: str | None) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_expire_days)
        await self.session.execute(
            text(
                '''
                INSERT INTO auth.refresh_tokens (user_id, token_hash, device_info, ip_address, expires_at)
                VALUES (:user_id, :token_hash, :device_info, CAST(:ip_address AS inet), :expires_at)
                '''
            ),
            {
                "user_id": str(user_id),
                "token_hash": self.hash_token(token),
                "device_info": device_info,
                "ip_address": ip_address,
                "expires_at": expires_at,
            },
        )

    async def refresh_token_is_valid(self, token: str) -> bool:
        result = await self.session.execute(
            text(
                '''
                SELECT 1 FROM auth.refresh_tokens
                WHERE token_hash=:token_hash AND revoked_at IS NULL AND expires_at > now()
                '''
            ),
            {"token_hash": self.hash_token(token)},
        )
        return result.first() is not None

    async def revoke_refresh_token(self, token: str) -> None:
        await self.session.execute(
            text("UPDATE auth.refresh_tokens SET revoked_at=now() WHERE token_hash=:token_hash AND revoked_at IS NULL"),
            {"token_hash": self.hash_token(token)},
        )

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(f"{token}{self.settings.jwt_secret_key}".encode()).hexdigest()
