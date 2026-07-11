import asyncio
from uuid import uuid4

from infrastructure.database.repositories.pg_student_repository import PgStudentRepository


class _FakeMappings:
    def all(self):
        return []


class _FakeResult:
    def mappings(self):
        return _FakeMappings()


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _FakeResult()


def _make_repo(monkeypatch):
    from config import settings as settings_module

    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: type("S", (), {"db_encryption_key": "test-key"})(),
    )
    session = _FakeSession()
    repo = PgStudentRepository(session)
    return repo, session


def test_non_privileged_requester_filters_by_teacher_id(monkeypatch):
    repo, session = _make_repo(monkeypatch)
    teacher_id = uuid4()
    institution_id = uuid4()

    asyncio.run(repo.list_students(teacher_id, is_privileged=False, institution_id=institution_id))

    query, params = session.calls[0]
    assert "g.teacher_id = :teacher_id" in query
    assert params["teacher_id"] == str(teacher_id)
    assert "g.school_id = :institution_id" in query
    assert params["institution_id"] == str(institution_id)


def test_privileged_requester_has_no_teacher_filter(monkeypatch):
    repo, session = _make_repo(monkeypatch)
    institution_id = uuid4()

    asyncio.run(repo.list_students(uuid4(), is_privileged=True, institution_id=institution_id))

    query, params = session.calls[0]
    assert "teacher_id" not in query
    assert "teacher_id" not in params
    assert params["institution_id"] == str(institution_id)


def test_grade_filter_applied_when_provided(monkeypatch):
    repo, session = _make_repo(monkeypatch)

    asyncio.run(repo.list_students(uuid4(), is_privileged=True, institution_id=uuid4(), grade=3))

    query, params = session.calls[0]
    assert "g.grade = :grade" in query
    assert params["grade"] == 3
