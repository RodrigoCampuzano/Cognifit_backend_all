import asyncio

from infrastructure.pln.health_registry import HealthRegistry


class _FakeClient:
    def __init__(self, status: str) -> None:
        self._status = status

    async def health(self) -> dict:
        return {"status": self._status}


def test_snapshot_is_none_before_first_refresh():
    registry = HealthRegistry()
    assert registry.snapshot() is None


def test_refresh_populates_snapshot_and_returns_it():
    registry = HealthRegistry()
    diagnosis = _FakeClient("ok")
    recommendation = _FakeClient("ok")

    result = asyncio.run(registry.refresh(diagnosis, recommendation))

    assert result["status"] == "ok"
    assert "checked_at" in result
    assert registry.snapshot() == result


def test_refresh_marks_degraded_if_any_client_unhealthy():
    registry = HealthRegistry()
    diagnosis = _FakeClient("ok")
    recommendation = _FakeClient("error")

    result = asyncio.run(registry.refresh(diagnosis, recommendation))

    assert result["status"] == "degraded"
