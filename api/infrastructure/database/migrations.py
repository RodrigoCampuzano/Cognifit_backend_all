from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_MIGRATIONS = [
    Path(__file__).resolve().parent / "seeds" / "005_seed_test_items.sql",
    Path(__file__).resolve().parent / "seeds" / "006_reseed_items.sql",
]


async def run_pending_migrations() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await _ensure_tracking_table(session)
            for path in _MIGRATIONS:
                if not path.exists():
                    logger.warning("Migration file not found: %s", path)
                    continue
                name = path.name
                if await _is_applied(session, name):
                    logger.debug("Migration already applied: %s", name)
                    continue
                logger.info("Applying migration: %s", name)
                sql = path.read_text(encoding="utf-8")
                # asyncpg's simple query protocol supports multiple statements.
                # Access it via the raw driver connection to bypass SQLAlchemy's
                # prepared-statement path (extended protocol), which does not.
                conn = await session.connection()
                raw = await conn.get_raw_connection()
                await raw.driver_connection.execute(sql)
                await _mark_applied(session, name)
                await session.commit()
                logger.info("Migration applied: %s", name)
        except Exception as exc:
            logger.error("Migration error: %s", exc)
            await session.rollback()


async def _ensure_tracking_table(session: AsyncSession) -> None:
    await session.execute(text("CREATE SCHEMA IF NOT EXISTS infrastructure"))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS infrastructure.applied_migrations (
            name TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.commit()


async def _is_applied(session: AsyncSession, name: str) -> bool:
    row = await session.execute(
        text("SELECT 1 FROM infrastructure.applied_migrations WHERE name = :name"),
        {"name": name},
    )
    return row.first() is not None


async def _mark_applied(session: AsyncSession, name: str) -> None:
    await session.execute(
        text("INSERT INTO infrastructure.applied_migrations (name) VALUES (:name) ON CONFLICT DO NOTHING"),
        {"name": name},
    )
