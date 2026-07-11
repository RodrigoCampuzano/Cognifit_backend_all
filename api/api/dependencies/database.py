from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import AsyncSessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def apply_rls_context(session: AsyncSession, *, user_id: str, role: str, institution_id: str | None = None) -> None:
    await session.execute(text("SELECT set_config('app.current_user_id', :user_id, true)"), {"user_id": user_id})
    await session.execute(text("SELECT set_config('app.current_user_role', :role, true)"), {"role": role})
    await session.execute(
        text("SELECT set_config('app.current_institution_id', :institution_id, true)"),
        {"institution_id": institution_id or ""},
    )
