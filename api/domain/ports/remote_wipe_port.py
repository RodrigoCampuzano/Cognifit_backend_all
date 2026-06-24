from __future__ import annotations

from typing import Protocol


class RemoteWipePort(Protocol):
    async def trigger_wipe(self, user_id: str, device_id: str | None, reason: str) -> dict: ...
