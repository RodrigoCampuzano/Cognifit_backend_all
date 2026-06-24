from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from security.audit.audit_logger import AuditLogger


class PgAuditRepository(AuditLogger):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
