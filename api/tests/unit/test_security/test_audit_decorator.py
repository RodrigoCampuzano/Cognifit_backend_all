import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent


@dataclass
class _FakeClient:
    host: str = "127.0.0.1"


@dataclass
class _FakeRequest:
    client: _FakeClient = field(default_factory=_FakeClient)
    headers: dict = field(default_factory=lambda: {"user-agent": "pytest"})


@dataclass
class _FakeUser:
    id: object = field(default_factory=uuid4)
    role: str = "ADMIN"


def test_audited_logs_after_successful_call(monkeypatch):
    logged = {}

    async def fake_log(self, session, **kwargs):
        logged.update(kwargs)

    from security.audit import audit_logger

    monkeypatch.setattr(audit_logger.AuditLogger, "log", fake_log)

    @audited(AuditEvent.REGISTER_STUDENT, target_table="academic.students")
    async def endpoint(*, request, db, user):
        return {"id": "abc-123"}

    result = asyncio.run(
        endpoint(request=_FakeRequest(), db=object(), user=_FakeUser())
    )

    assert result == {"id": "abc-123"}
    assert logged["action"] == AuditEvent.REGISTER_STUDENT.value
    assert logged["target_table"] == "academic.students"
    assert logged["target_id"] == "abc-123"


def test_audited_uses_target_id_arg(monkeypatch):
    logged = {}

    async def fake_log(self, session, **kwargs):
        logged.update(kwargs)

    from security.audit import audit_logger

    monkeypatch.setattr(audit_logger.AuditLogger, "log", fake_log)

    @audited(AuditEvent.DELETE_STUDENT, target_table="academic.students", target_id_arg="student_id")
    async def endpoint(*, student_id, request, db, user):
        return None

    asyncio.run(
        endpoint(student_id="s-1", request=_FakeRequest(), db=object(), user=_FakeUser())
    )

    assert logged["target_id"] == "s-1"


def test_audited_skips_when_condition_false(monkeypatch):
    called = False

    async def fake_log(self, session, **kwargs):
        nonlocal called
        called = True

    from security.audit import audit_logger

    monkeypatch.setattr(audit_logger.AuditLogger, "log", fake_log)

    @audited(
        AuditEvent.ALERT_GENERATED,
        target_table="tracking.alerts",
        condition=lambda result: bool(result.get("alert")),
    )
    async def endpoint(*, request, db, user):
        return {"alert": None}

    asyncio.run(endpoint(request=_FakeRequest(), db=object(), user=_FakeUser()))

    assert called is False
