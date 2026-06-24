from __future__ import annotations

import hashlib
import json

from infrastructure.cache.redis_client import get_redis


class SemanticCache:
    async def get(self, namespace: str, payload: dict) -> dict | None:
        redis = get_redis()
        if not redis:
            return None
        raw = await redis.get(self._key(namespace, payload))
        return json.loads(raw) if raw else None

    async def set(self, namespace: str, payload: dict, value: dict, ttl: int = 3600) -> None:
        redis = get_redis()
        if not redis:
            return
        await redis.setex(self._key(namespace, payload), ttl, json.dumps(value))

    def _key(self, namespace: str, payload: dict) -> str:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return f"semantic:{namespace}:{digest}"
