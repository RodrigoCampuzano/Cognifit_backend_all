from __future__ import annotations

import functools
import inspect
import typing
from typing import Callable

from fastapi.encoders import jsonable_encoder

from infrastructure.cache.semantic_cache import SemanticCache


def cached_endpoint(
    namespace: str, ttl: int = 3600, key_params: tuple[str, ...] = ()
) -> Callable:
    """Decorator (GoF): envuelve un endpoint FastAPI para servir desde Redis
    (SemanticCache) cuando hay hit, degradando con gracia si Redis no está
    configurado (SemanticCache.get devuelve None en ese caso).

    `key_params` nombra los argumentos que forman parte de la clave. Sin él la
    clave era solo el namespace, así que un endpoint con parámetros servía la
    primera respuesta a todo el mundo. Concretamente: el cuestionario docente
    devuelve ítems distintos según el ciclo del alumno, y sin esto un niño de
    6º habría recibido los de 1º porque fue la primera respuesta cacheada.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = SemanticCache()
            payload = {"namespace": namespace}
            for nombre in key_params:
                payload[nombre] = kwargs.get(nombre)
            hit = await cache.get(namespace, payload)
            if hit is not None:
                return hit
            result = await func(*args, **kwargs)
            encoded = jsonable_encoder(result)
            await cache.set(namespace, payload, encoded, ttl=ttl)
            return encoded

        # Ver el comentario equivalente en security/audit/audit_decorator.py:
        # sin esto, FastAPI resuelve las anotaciones de tipo del endpoint
        # contra los globals de este módulo (no los del router original), y
        # con `from __future__ import annotations` eso rompe con parámetros
        # como UUID en cuanto llega una petición real.
        resolved_hints = typing.get_type_hints(func)
        original_sig = inspect.signature(func)
        wrapper.__signature__ = original_sig.replace(
            parameters=[
                param.replace(annotation=resolved_hints.get(name, param.annotation))
                for name, param in original_sig.parameters.items()
            ]
        )
        return wrapper

    return decorator
