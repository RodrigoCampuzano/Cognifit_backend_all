"""El orden en que se presentan los ítems de una sesión no es un detalle
cosmético: define qué se está midiendo.

Tres propiedades que deben convivir, y que se rompen con facilidad al tocar la
consulta:

  1. Los ítems de práctica van primero.
  2. La dificultad va de menor a mayor.
  3. Dentro de cada nivel el orden cambia entre sesiones.

La tercera existe porque el tamizaje se repite cada cierto tiempo y el alumno
no debe poder memorizar la secuencia. La segunda existe porque el banco está
construido con progresión de dificultad, y saltearla cambia el resultado: un
alumno que se topa con lo más difícil al principio se frustra, y lo que se
mide deja de ser su lectura.

Estuvieron en conflicto: la consulta barajaba con MD5 sin mirar `difficulty`,
así que repartía los tres niveles al azar desde el primer ítem.
"""
import inspect
import re


def _consulta_de_items() -> str:
    from infrastructure.database.repositories.pg_session_repository import (
        PgSessionRepository,
    )

    return inspect.getsource(PgSessionRepository.get_session_items)


def _clausula_order_by(sql: str) -> str:
    m = re.search(r"ORDER BY(.*?)'''", sql, re.S)
    assert m, "no se encontró el ORDER BY de get_session_items"
    # Se descartan los comentarios SQL para comparar solo la cláusula.
    return " ".join(
        linea.split("--")[0].strip()
        for linea in m.group(1).splitlines()
    ).strip()


def test_los_items_de_practica_van_primero():
    assert "is_practice DESC" in _clausula_order_by(_consulta_de_items())


def test_la_dificultad_va_de_menor_a_mayor():
    assert "difficulty ASC" in _clausula_order_by(_consulta_de_items())


def test_el_orden_cambia_entre_sesiones():
    """Sin esto, un alumno que repite el tamizaje ve siempre la misma
    secuencia y puede memorizar las respuestas."""
    orden = _clausula_order_by(_consulta_de_items())
    assert "MD5" in orden
    assert "session_id" in orden, (
        "el barajado debe depender de la sesión; si no, es igual para todos"
    )


def test_la_dificultad_pesa_mas_que_el_barajado():
    """El orden de la cláusula importa: si MD5 fuera antes que difficulty, el
    azar volvería a repartir los niveles y la progresión se perdería."""
    orden = _clausula_order_by(_consulta_de_items())
    assert orden.index("difficulty ASC") < orden.index("MD5"), (
        "difficulty debe ir ANTES que el MD5 en el ORDER BY"
    )


def test_el_barajado_es_reproducible_dentro_de_la_sesion():
    """Se usa el id de la sesión y no random(): si la app vuelve a pedir los
    ítems de la misma sesión, debe recibirlos en el mismo orden."""
    orden = _clausula_order_by(_consulta_de_items())
    assert "random()" not in orden.lower()
