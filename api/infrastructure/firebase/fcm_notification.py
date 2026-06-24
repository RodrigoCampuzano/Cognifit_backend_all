from __future__ import annotations


class FcmNotification:
    async def send(self, target: str, title: str, body: str, data: dict | None = None) -> None:
        return None
