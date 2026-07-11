from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, get_current_user, get_optional_current_user, require_roles
from api.dependencies.database import get_db
from api.v1.auth.schemas import CurrentUserResponse, LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterUserRequest, TokenPair
from config.settings import get_settings
from infrastructure.security.jwt_service import JWTService
from infrastructure.security.password_hasher import Argon2PasswordHasher
from infrastructure.security.user_repository import UserRepository
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(db: AsyncSession, user: dict, request: Request, device_info: str | None = None) -> TokenPair:
    settings = get_settings()
    jwt_service = JWTService()
    access = jwt_service.create_access_token(
        user_id=user["id"], email=user["email"], role=user["role"], institution_id=user.get("institution_id")
    )
    refresh = jwt_service.create_refresh_token(user_id=user["id"])
    repo = UserRepository(db)
    await repo.store_refresh_token(
        user_id=user["id"],
        token=refresh,
        device_info=device_info,
        ip_address=request.client.host if request.client else None,
    )
    return TokenPair(access_token=access, refresh_token=refresh, expires_in_minutes=settings.access_token_expire_minutes)


@router.post("/register", response_model=CurrentUserResponse, status_code=201)
async def register_user(
    payload: RegisterUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
):
    settings = get_settings()
    if current_user and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can create users")
    if not current_user and (settings.is_production or not settings.allow_public_registration):
        raise HTTPException(status_code=403, detail="Public registration disabled")
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    password_hash = Argon2PasswordHasher().hash(payload.password)
    try:
        user = await repo.create_user(
            email=payload.email,
            password_hash=password_hash,
            role=payload.role,
            institution_id=current_user.institution_id if current_user else None,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario: falta institución") from exc
    await AuditLogger().log(
        db,
        action=AuditEvent.REGISTER_USER.value,
        actor_id=current_user.id if current_user else user["id"],
        actor_role=current_user.role if current_user else user["role"],
        target_table="auth.users",
        target_id=user["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if not user or not user["is_active"] or not Argon2PasswordHasher().verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user["role"] != "SUPERADMIN" and not user["institution_is_active"]:
        raise HTTPException(status_code=403, detail="Tu institución está pendiente de aprobación")
    tokens = await _issue_tokens(db, user, request, payload.device_info)
    await AuditLogger().log(
        db,
        action=AuditEvent.LOGIN.value,
        actor_id=user["id"],
        actor_role=user["role"],
        target_table="auth.users",
        target_id=user["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return tokens


@router.post("/token", response_model=TokenPair, include_in_schema=True)
async def token_for_swagger(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get_by_email(form.username)
    if not user or not user["is_active"] or not Argon2PasswordHasher().verify(form.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user["role"] != "SUPERADMIN" and not user["institution_is_active"]:
        raise HTTPException(status_code=403, detail="Tu institución está pendiente de aprobación")
    return await _issue_tokens(db, user, request, "swagger")


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshTokenRequest, request: Request, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    try:
        decoded = JWTService().decode(payload.refresh_token, expected_type="refresh")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if not await repo.refresh_token_is_valid(payload.refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")
    user = await repo.get_by_id(decoded["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User inactive")
    return await _issue_tokens(db, user, request, "refresh")


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    await UserRepository(db).revoke_refresh_token(payload.refresh_token)
    await AuditLogger().log(db, action=AuditEvent.LOGOUT.value, actor_id=user.id, actor_role=user.role)
    return None


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    record = await UserRepository(db).get_by_id(user.id)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    return record
