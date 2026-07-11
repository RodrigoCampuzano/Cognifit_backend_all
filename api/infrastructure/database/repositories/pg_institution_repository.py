from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgInstitutionRepository:
    """Alta y aprobación de instituciones (escuelas). Una escuela nueva se
    autorregistra inactiva; solo un SUPERADMIN puede activarla."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self, *, name: str, cct: str | None, state: str, municipality: str | None
    ) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO academic.schools (name, cct, state, municipality)
                VALUES (:name, :cct, :state, :municipality)
                RETURNING id, name, cct, state, municipality, is_active, created_at, approved_at
                '''
            ),
            {"name": name, "cct": cct, "state": state, "municipality": municipality},
        )
        return dict(result.mappings().one())

    async def list_pending(self) -> list[dict]:
        result = await self.session.execute(
            text(
                '''
                SELECT id, name, cct, state, municipality, is_active, created_at, approved_at
                FROM academic.schools
                WHERE is_active = FALSE
                ORDER BY created_at ASC
                '''
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def approve(self, institution_id: UUID, *, approved_by: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                UPDATE academic.schools
                SET is_active = TRUE, approved_at = now(), approved_by = :approved_by
                WHERE id = :id
                RETURNING id, name, cct, state, municipality, is_active, created_at, approved_at
                '''
            ),
            {"id": str(institution_id), "approved_by": str(approved_by)},
        )
        row = result.mappings().first()
        return dict(row) if row else None
