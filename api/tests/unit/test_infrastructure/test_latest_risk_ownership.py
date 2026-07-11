import asyncio
from uuid import uuid4


class _FakeMappings:
    def first(self):
        return None


class _FakeResult:
    def mappings(self):
        return _FakeMappings()


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _FakeResult()


def test_get_latest_risk_query_includes_institution_and_ownership_clause():
    """IDOR: get_latest_risk debe filtrar por institución y, si no es
    privilegiado, también por docente/padre — nunca devolver el riesgo de un
    alumno solo por su UUID."""
    from infrastructure.database.repositories.pg_result_repository import PgResultRepository

    session = _FakeSession()
    repo = PgResultRepository(session)
    student_id = uuid4()
    requester_id = uuid4()
    institution_id = uuid4()

    asyncio.run(
        repo.get_latest_risk(student_id, requester_id=requester_id, is_privileged=False, institution_id=institution_id)
    )

    query, params = session.calls[0]
    assert "g.school_id = :institution_id" in query
    assert "g.teacher_id = :requester_id" in query
    assert "s.parent_user_id = :requester_id" in query
    assert params["institution_id"] == str(institution_id)
    assert params["requester_id"] == str(requester_id)
    assert params["is_privileged"] is False


def test_get_latest_risk_privileged_still_scoped_to_institution():
    from infrastructure.database.repositories.pg_result_repository import PgResultRepository

    session = _FakeSession()
    repo = PgResultRepository(session)
    institution_id = uuid4()

    asyncio.run(
        repo.get_latest_risk(uuid4(), requester_id=uuid4(), is_privileged=True, institution_id=institution_id)
    )

    query, params = session.calls[0]
    assert "g.school_id = :institution_id" in query
    assert params["institution_id"] == str(institution_id)
    assert params["is_privileged"] is True
