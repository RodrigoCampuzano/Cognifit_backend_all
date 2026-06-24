from __future__ import annotations


class FcmRemoteWipe:
    async def trigger_wipe(self, user_id: str, device_id: str | None, reason: str) -> dict:
        return {"queued": True, "user_id": user_id, "device_id": device_id, "reason": reason}
