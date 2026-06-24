from __future__ import annotations

from typing import Protocol


class NotificationPort(Protocol):
    async def send(self, target: str, title: str, body: str, data: dict | None = None) -> None: ...
