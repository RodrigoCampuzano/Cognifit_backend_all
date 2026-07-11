from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import apply_rls_context, get_db
from config.settings import get_settings
from infrastructure.security.jwt_service import JWTService
from security.policies.rbac import has_role

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")
optional_bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class CurrentUser:
    id: UUID
    email: str
    role: str
    institution_id: UUID | None = None


def _parse_current_user(payload: dict) -> CurrentUser:
    raw_institution_id = payload.get("institution_id")
    return CurrentUser(
        id=UUID(payload["sub"]),
        email=payload["email"],
        role=payload["role"],
        institution_id=UUID(raw_institution_id) if raw_institution_id else None,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    try:
        payload = JWTService().decode(token, expected_type="access")
        user = _parse_current_user(payload)
        await apply_rls_context(db, user_id=str(user.id), role=user.role, institution_id=str(user.institution_id) if user.institution_id else None)
        return user
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser | None:
    if credentials is None:
        return None
    try:
        payload = JWTService().decode(credentials.credentials, expected_type="access")
        user = _parse_current_user(payload)
        await apply_rls_context(db, user_id=str(user.id), role=user.role, institution_id=str(user.institution_id) if user.institution_id else None)
        return user
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_roles(*roles: str):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_role(user.role, set(roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
