from __future__ import annotations

import functools
from typing import Callable

from fastapi.encoders import jsonable_encoder

from infrastructure.cache.semantic_cache import SemanticCache


def cached_endpoint(namespace: str, ttl: int = 3600) -> Callable:
    """Decorator (GoF): envuelve un endpoint FastAPI para servir desde Redis
    (SemanticCache) cuando hay hit, degradando con gracia si Redis no está
    configurado (SemanticCache.get devuelve None en ese caso)."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = SemanticCache()
            payload = {"namespace": namespace}
            hit = await cache.get(namespace, payload)
            if hit is not None:
                return hit
            result = await func(*args, **kwargs)
            encoded = jsonable_encoder(result)
            await cache.set(namespace, payload, encoded, ttl=ttl)
            return encoded

        return wrapper

    return decorator
