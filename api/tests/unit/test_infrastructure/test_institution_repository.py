import asyncio
from uuid import uuid4


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def one(self):
        return self._rows[0]

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _FakeMappings(self._rows)


class _FakeSession:
    def __init__(self, row=None) -> None:
        self.calls: list[tuple] = []
        self._row = row

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _FakeResult([self._row] if self._row else [])


def test_register_inserts_inactive_school(monkeypatch):
    from infrastructure.database.repositories.pg_institution_repository import PgInstitutionRepository

    fake_row = {"id": uuid4(), "name": "Escuela Test", "cct": None, "state": "Chiapas", "municipality": None, "is_active": False, "created_at": None, "approved_at": None}
    session = _FakeSession(fake_row)
    repo = PgInstitutionRepository(session)

    result = asyncio.run(repo.register(name="Escuela Test", cct=None, state="Chiapas", municipality=None))

    assert result["is_active"] is False
    query, params = session.calls[0]
    assert "INSERT INTO academic.schools" in query
    assert params["name"] == "Escuela Test"


def test_approve_sets_active_and_approver(monkeypatch):
    from infrastructure.database.repositories.pg_institution_repository import PgInstitutionRepository

    institution_id = uuid4()
    approver_id = uuid4()
    fake_row = {"id": institution_id, "name": "Escuela Test", "cct": None, "state": "Chiapas", "municipality": None, "is_active": True, "created_at": None, "approved_at": None}
    session = _FakeSession(fake_row)
    repo = PgInstitutionRepository(session)

    result = asyncio.run(repo.approve(institution_id, approved_by=approver_id))

    assert result["is_active"] is True
    query, params = session.calls[0]
    assert "SET is_active = TRUE" in query
    assert params["approved_by"] == str(approver_id)


def test_approve_returns_none_when_not_found():
    from infrastructure.database.repositories.pg_institution_repository import PgInstitutionRepository

    session = _FakeSession(row=None)
    repo = PgInstitutionRepository(session)

    result = asyncio.run(repo.approve(uuid4(), approved_by=uuid4()))

    assert result is None
