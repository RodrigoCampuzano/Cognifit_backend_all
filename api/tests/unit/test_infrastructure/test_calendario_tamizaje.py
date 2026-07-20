"""El calendario decide qué se le aplica a cada alumno y cada cuánto.

Dos cadencias porque responden preguntas distintas: el monitoreo mensual dice
si está avanzando, la batería cuatrimestral si su perfil cambió.

La separación no es una preferencia de diseño: siete de los nueve módulos no
tienen banco para muestrear, así que aplicarlos cada mes haría que el alumno
repita ítems idénticos. La curva subiría por práctica y se concluiría que la
intervención funciona donde quizá no lo hace.
"""
import inspect


def _consulta() -> str:
    from infrastructure.database.repositories.pg_session_repository import (
        PgSessionRepository,
    )

    return inspect.getsource(PgSessionRepository.get_calendario_tamizaje)


def test_acotado_a_la_institucion():
    """Sin esto un docente vería el calendario de alumnos de otras escuelas."""
    assert "g.school_id = :institution_id" in _consulta()


def test_un_docente_no_privilegiado_solo_ve_sus_grupos():
    sql = _consulta()
    assert "is_privileged" in sql
    assert "g.teacher_id = :teacher_id" in sql


def test_el_nombre_se_descifra():
    """`full_name` es BYTEA cifrado con pgcrypto; leerlo crudo devuelve bytes
    y rompe la respuesta."""
    assert "pgp_sym_decrypt(s.full_name, :key)" in _consulta()


def test_primero_quien_nunca_fue_evaluado():
    """Sin línea base no hay con qué comparar lo que venga después, así que
    esos alumnos encabezan la lista."""
    sql = _consulta()
    assert "BATERIA_INICIAL" in sql
    assert sql.index("BATERIA_INICIAL") < sql.index("MONITOREO"), (
        "el orden de prioridad debe poner la línea base primero"
    )


def test_no_usa_interpolacion_de_valores_en_sql():
    """La cláusula WHERE se arma dinámicamente. Lo que se interpola son
    fragmentos literales del código; los valores van siempre ligados."""
    sql = _consulta()
    # Los tres parámetros del método viajan como bind params.
    for p in (":institution_id", ":teacher_id", ":key"):
        assert p in sql
    # Y no aparecen interpolados dentro del f-string.
    assert "{institution_id}" not in sql
    assert "{teacher_id}" not in sql
