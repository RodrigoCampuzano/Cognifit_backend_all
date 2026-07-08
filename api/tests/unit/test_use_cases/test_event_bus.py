import asyncio

from application.services.event_bus import EventBus
from domain.events.base_event import DomainEvent


class _DummyEvent(DomainEvent):
    pass


class _OtherEvent(DomainEvent):
    pass


def test_publish_calls_subscribed_handler():
    bus = EventBus()
    calls = []

    async def handler(session, event):
        calls.append(event)
        return "handled"

    bus.subscribe(_DummyEvent, handler)
    result = asyncio.run(bus.publish(None, _DummyEvent()))

    assert result == ["handled"]
    assert len(calls) == 1


def test_publish_without_subscribers_returns_empty_list():
    bus = EventBus()
    result = asyncio.run(bus.publish(None, _OtherEvent()))
    assert result == []


def test_publish_only_notifies_matching_event_type():
    bus = EventBus()
    dummy_calls = []
    other_calls = []

    async def dummy_handler(session, event):
        dummy_calls.append(event)

    async def other_handler(session, event):
        other_calls.append(event)

    bus.subscribe(_DummyEvent, dummy_handler)
    bus.subscribe(_OtherEvent, other_handler)

    asyncio.run(bus.publish(None, _DummyEvent()))

    assert len(dummy_calls) == 1
    assert len(other_calls) == 0
