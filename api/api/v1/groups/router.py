from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.v1.groups.schemas import CreateGroupRequest, GroupResponse
from infrastructure.database.repositories.pg_group_repository import PgGroupRepository
from uuid import UUID

from fastapi import HTTPException
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    return await PgGroupRepository(db).list_groups(user.id, is_privileged=user.role in ("ADMIN", "SPECIALIST"))


@router.delete("/{group_id}", status_code=204)
@audited(AuditEvent.DELETE_GROUP, target_table="academic.groups", target_id_arg="group_id")
async def delete_group(
    group_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    try:
        await PgGroupRepository(db).delete_group(group_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("", response_model=GroupResponse, status_code=201)
@audited(AuditEvent.REGISTER_GROUP, target_table="academic.groups")
async def create_group(
    payload: CreateGroupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "TEACHER")),
):
    return await PgGroupRepository(db).create_group(user.id, payload.model_dump())
