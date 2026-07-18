"""Alerta automática de riesgo alto tras un tamizaje.

Antes, un diagnóstico HIGH no generaba ningún aviso: el docente solo se
enteraba si abría manualmente el perfil del alumno. Estas pruebas fijan el
comportamiento para que no se pierda en un refactor.
"""
import asyncio
from uuid import uuid4

from application.services.alert_observer import create_alert_on_high_risk


class _Row(tuple):
    """Fila estilo SQLAlchemy: indexable y con .first()."""


class _Result:
    def __init__(self, row=None, mapping=None):
        self._row = row
        self._mapping = mapping

    def first(self):
        return self._row

    def mappings(self):
        outer = self._mapping

        class _M:
            def one(self):
                return outer

        return _M()


class _FakeSession:
    """Devuelve respuestas encoladas y registra el SQL ejecutado."""

    def __init__(self, results):
        self._results = list(results)
        self.sql: list[str] = []
        self.params: list[dict] = []

    async def execute(self, statement, params=None):
        self.sql.append(" ".join(str(statement).split()))
        self.params.append(params or {})
        return self._results.pop(0)


def test_no_alerta_si_el_riesgo_no_es_alto():
    session = _FakeSession([])
    for nivel in ("LOW", "MEDIUM", None, ""):
        out = asyncio.run(
            create_alert_on_high_risk(
                session, student_id=uuid4(), pln_subtype="fonologico",
                pln_severity="leve", risk_level=nivel, risk_probability=0.2,
            )
        )
        assert out is None
    assert session.sql == [], "no debe tocar la base si el riesgo no es alto"


def test_crea_alerta_para_el_docente_del_grupo():
    teacher_id = uuid4()
    creada = {"id": uuid4(), "alert_type": "HIGH_RISK", "urgency": "HIGH",
              "message": "x", "created_at": None}
    session = _FakeSession([
        _Result(row=_Row((teacher_id,))),  # docente del grupo
        _Result(row=None),                 # no hay alerta previa sin leer
        _Result(mapping=creada),           # INSERT
    ])

    out = asyncio.run(
        create_alert_on_high_risk(
            session, student_id=uuid4(), pln_subtype="fonologico",
            pln_severity="severo", risk_level="HIGH", risk_probability=0.87,
        )
    )

    assert out["alert_type"] == "HIGH_RISK"
    insert = session.sql[-1]
    assert "INSERT INTO tracking.alerts" in insert
    assert "'HIGH_RISK'" in insert and "'HIGH'" in insert
    # El mensaje debe llevar el porcentaje y el perfil, que es lo que el
    # docente necesita para priorizar sin abrir el perfil completo.
    msg = session.params[-1]["msg"]
    assert "87%" in msg and "fonologico" in msg and "severo" in msg
    assert str(teacher_id) == session.params[-1]["tid"]


def test_no_duplica_alerta_no_leida_en_24h():
    session = _FakeSession([
        _Result(row=_Row((uuid4(),))),     # docente
        _Result(row=_Row((uuid4(),))),     # YA existe una alerta sin leer
    ])
    out = asyncio.run(
        create_alert_on_high_risk(
            session, student_id=uuid4(), pln_subtype="visual",
            pln_severity="moderado", risk_level="HIGH", risk_probability=0.7,
        )
    )
    assert out is None
    assert not any("INSERT INTO tracking.alerts" in s for s in session.sql)


def test_sin_docente_no_revienta():
    """Un alumno sin grupo/docente no debe romper el diagnóstico."""
    session = _FakeSession([_Result(row=None)])
    out = asyncio.run(
        create_alert_on_high_risk(
            session, student_id=uuid4(), pln_subtype="mixto",
            pln_severity="severo", risk_level="HIGH", risk_probability=0.9,
        )
    )
    assert out is None
