from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AuditLogger:
    async def log(
        self,
        session: AsyncSession,
        *,
        action: str,
        actor_id: UUID | str | None = None,
        actor_role: str | None = None,
        target_table: str | None = None,
        target_id: UUID | str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        await session.execute(
            text(
                '''
                INSERT INTO audit.audit_log
                    (actor_id, actor_role, action, target_table, target_id, ip_address, user_agent, metadata)
                VALUES
                    (:actor_id, CAST(:actor_role AS auth.user_role), :action, :target_table, :target_id, CAST(:ip_address AS inet), :user_agent, CAST(:metadata AS jsonb))
                '''
            ),
            {
                "actor_id": str(actor_id) if actor_id else None,
                "actor_role": actor_role,
                "action": action,
                "target_table": target_table,
                "target_id": str(target_id) if target_id else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "metadata": json.dumps(metadata or {}),
            },
        )
