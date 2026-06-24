from __future__ import annotations

from infrastructure.firebase.fcm_remote_wipe import FcmRemoteWipe


class TriggerWipeUseCase:
    def __init__(self, wipe: FcmRemoteWipe | None = None) -> None:
        self.wipe = wipe or FcmRemoteWipe()

    async def execute(self, user_id: str, device_id: str | None, reason: str) -> dict:
        return await self.wipe.trigger_wipe(user_id, device_id, reason)
