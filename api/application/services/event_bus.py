from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from domain.events.base_event import DomainEvent

Handler = Callable[[AsyncSession, DomainEvent], Awaitable[Any]]


class EventBus:
    """Subject (GoF Observer): desacopla a quien detecta un evento de dominio
    de quien reacciona a él. Los handlers corren dentro de la misma AsyncSession
    del request para no romper la atomicidad de la transacción (ADR-27)."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, session: AsyncSession, event: DomainEvent) -> list[Any]:
        return [await handler(session, event) for handler in self._subscribers[type(event)]]


@lru_cache
def get_event_bus() -> EventBus:
    return EventBus()
