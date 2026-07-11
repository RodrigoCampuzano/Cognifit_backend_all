import asyncio
from uuid import uuid4


class _FakeMappings:
    def first(self):
        return None


class _FakeResult:
    def mappings(self):
        return _FakeMappings()

    def first(self):
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _FakeResult()


def _make_repo(monkeypatch):
    from config import settings as settings_module
    from infrastructure.database.repositories.pg_student_repository import PgStudentRepository

    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: type("S", (), {"db_encryption_key": "test-key"})(),
    )
    session = _FakeSession()
    return PgStudentRepository(session), session


def test_get_student_query_includes_institution_and_ownership_clause(monkeypatch):
    """IDOR: get_student debe filtrar por institución y, si no es privilegiado,
    también por docente/padre — nunca devolver un alumno solo por su UUID."""
    repo, session = _make_repo(monkeypatch)
    student_id = uuid4()
    requester_id = uuid4()
    institution_id = uuid4()

    asyncio.run(
        repo.get_student(student_id, requester_id=requester_id, is_privileged=False, institution_id=institution_id)
    )

    query, params = session.calls[0]
    assert "g.school_id = :institution_id" in query
    assert "g.teacher_id = :requester_id" in query
    assert "s.parent_user_id = :requester_id" in query
    assert params["institution_id"] == str(institution_id)
    assert params["requester_id"] == str(requester_id)
    assert params["is_privileged"] is False


def test_register_student_validates_group_ownership_before_insert(monkeypatch):
    """Un TEACHER no debe poder crear alumnos en el grupo de otra institución
    pasando el group_id directamente."""
    repo, session = _make_repo(monkeypatch)
    requester_id = uuid4()
    institution_id = uuid4()

    try:
        asyncio.run(
            repo.register_student(
                {"group_id": uuid4(), "full_name": "Test"},
                requester_id=requester_id,
                is_privileged=False,
                institution_id=institution_id,
            )
        )
        raised = False
    except ValueError:
        raised = True

    # La sesión fake siempre devuelve "no encontrado" -> debe fallar cerrado.
    assert raised is True
    query, params = session.calls[0]
    assert "FROM academic.groups" in query
    assert params["institution_id"] == str(institution_id)
