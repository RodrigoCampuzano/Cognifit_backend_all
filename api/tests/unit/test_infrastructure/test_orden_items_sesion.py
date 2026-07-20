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
    # El ÚLTIMO ORDER BY: la consulta tiene otro antes, dentro de la función de
    # ventana que numera los ítems de cada nivel de dificultad.
    i = sql.rfind("ORDER BY")
    assert i != -1, "no se encontró el ORDER BY de get_session_items"
    m = re.match(r"ORDER BY(.*?)'''", sql[i:], re.S)
    assert m, "no se pudo delimitar el ORDER BY final"
    # Se descartan los comentarios SQL para comparar solo la cláusula.
    return " ".join(
        linea.split("--")[0].strip()
        for linea in m.group(1).splitlines()
    ).strip()


def test_los_items_de_practica_van_primero():
    assert "is_practice DESC" in _clausula_order_by(_consulta_de_items())


def test_la_dificultad_va_de_menor_a_mayor():
    # Va dentro de un CASE porque la denominación rápida usa item_order en su
    # lugar; la propiedad que importa es que la dificultad gobierne el orden
    # de los módulos normales.
    assert "ELSE difficulty END ASC" in _clausula_order_by(_consulta_de_items())


def test_el_orden_cambia_entre_sesiones():
    """Sin esto, un alumno que repite el tamizaje ve siempre la misma
    secuencia y puede memorizar las respuestas."""
    orden = _clausula_order_by(_consulta_de_items())
    assert "MD5" in orden
    assert "session_id" in orden, (
        "el barajado debe depender de la sesión; si no, es igual para todos"
    )


def test_la_dificultad_pesa_mas_que_el_barajado():
    """El orden de las claves importa: si el MD5 fuera antes que la dificultad,
    el azar volvería a repartir los niveles y la progresión se perdería."""
    orden = _clausula_order_by(_consulta_de_items())
    assert orden.index("ELSE difficulty END") < orden.index("MD5"), (
        "la dificultad debe ir ANTES que el MD5 en el ORDER BY"
    )


def test_el_barajado_es_reproducible_dentro_de_la_sesion():
    """Se usa el id de la sesión y no random(): si la app vuelve a pedir los
    ítems de la misma sesión, debe recibirlos en el mismo orden."""
    orden = _clausula_order_by(_consulta_de_items())
    assert "random()" not in orden.lower()


# ─── Muestreo estratificado ──────────────────────────────────────────────────
# Barajar el orden evita que el alumno memorice la SECUENCIA. Para que no
# memorice las RESPUESTAS hace falta que no vea siempre los mismos ítems, y
# eso es lo que hace el muestreo. Conservar la proporción de cada nivel es lo
# que mantiene comparables dos aplicaciones del tamizaje.


def test_hay_muestreo_por_sesion():
    sql = _consulta_de_items()
    assert "items_per_session" in sql, (
        "sin muestreo el alumno ve el banco entero cada vez y puede "
        "memorizar las respuestas"
    )


def test_el_muestreo_es_proporcional_a_cada_nivel():
    """La cuota de cada dificultad sale de su peso en el banco. Con muestreo
    aleatorio simple una mejora entre dos aplicaciones podría ser solo que la
    segunda muestra salió más fácil."""
    sql = _consulta_de_items()
    assert "PARTITION BY ti.difficulty" in sql
    assert "total_nivel" in sql and "total_banco" in sql


def test_los_items_de_practica_nunca_se_muestrean():
    sql = _consulta_de_items()
    assert "WHERE is_practice" in sql, (
        "la práctica debe presentarse siempre, no entrar en el sorteo"
    )


def test_sin_items_per_session_se_entrega_el_banco_entero():
    """NULL es el valor correcto para los módulos cuyo banco ya tiene el
    tamaño de una sesión; no deben quedar truncados."""
    assert "items_per_session IS NULL" in _consulta_de_items()


def test_denominacion_rapida_conserva_su_lamina_y_su_orden():
    """Su medida es el tiempo total de nombrar una lámina fija. Cambiar los
    ítems o su orden invalida la comparación entre alumnos y entre
    aplicaciones — el mismo criterio que en los juegos de cuadrícula."""
    sql = _consulta_de_items()
    assert "RAPID_NAMING" in sql
    assert "orden_fijo" in sql
    # Se excluye del muestreo...
    assert "OR orden_fijo" in sql
    # ...y del barajado, ordenándose por su item_order.
    assert "THEN item_order" in sql
