from __future__ import annotations

import functools
import inspect
import typing
from typing import Any, Callable

from api.dependencies.auth import CurrentUser
from security.audit.audit_events import AuditEvent
from security.audit.audit_logger import AuditLogger


def audited(
    event: AuditEvent,
    *,
    target_table: str | None = None,
    target_id_arg: str | None = None,
    target_id_fn: Callable[[Any, dict], Any] | None = None,
    metadata_fn: Callable[[Any, dict], dict | None] | None = None,
    condition: Callable[[Any], bool] | None = None,
):
    """Decorator (GoF): registra automáticamente un AuditEvent tras una operación
    exitosa del endpoint decorado, reemplazando el bloque `await AuditLogger().log(...)`
    que antes se repetía manualmente en cada router.

    Requiere que el endpoint reciba `request: Request`, `db: AsyncSession` y
    `user: CurrentUser` como parámetros nombrados (ya inyectados vía Depends en
    todos los routers de escritura donde se aplica).

    - target_id_arg: nombre del parámetro de path/query que es el target_id
      (para deletes/updates donde el retorno no trae 'id' útil).
    - target_id_fn: alternativa más flexible (result, kwargs) -> target_id,
      para casos donde el id está anidado.
    - condition: si se define y devuelve False, no se audita (ej. solo auditar
      cuando efectivamente se generó una alerta).
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if condition is not None and not condition(result):
                return result
            request = kwargs["request"]
            db = kwargs["db"]
            user: CurrentUser = kwargs["user"]
            if target_id_fn:
                target_id = target_id_fn(result, kwargs)
            elif target_id_arg:
                target_id = kwargs[target_id_arg]
            else:
                target_id = result.get("id") if isinstance(result, dict) else None
            await AuditLogger().log(
                db,
                action=event.value,
                actor_id=user.id,
                actor_role=user.role,
                target_table=target_table,
                target_id=target_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata=metadata_fn(result, kwargs) if metadata_fn else None,
            )
            return result

        # FastAPI resuelve los parámetros de la ruta usando wrapper.__globals__
        # (el módulo de ESTE decorator), no los de func (el router original).
        # Con `from __future__ import annotations` en los routers, anotaciones
        # como `UUID` quedan como texto ("UUID") hasta que algo las resuelve —
        # y como este módulo nunca importó UUID, la resolución fallaba con
        # PydanticUserError en cualquier request real (no lo detecta
        # app.openapi(), solo una petición HTTP real). Reconstruir la firma acá,
        # resuelta contra los globals correctos de func, evita el problema de raíz.
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
