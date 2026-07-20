"""El percentil del TEDE acompaña a la severidad del modelo.

Importa porque el modelo se entrenó con datos sintéticos y no tiene una sola
etiqueta de especialista con la cual validarse, mientras que el TEDE trae
baremos estandarizados. Las tablas estaban digitalizadas desde hacía tiempo y
nadie las llamaba: eran código muerto.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tede_scoring import percentil_nivel_lector, tede_percentil


def _items(aciertos: int, total: int, modulo: str = "lectura_voz_alta"):
    return [
        {"module": modulo, "is_correct": i < aciertos}
        for i in range(total)
    ]


def test_un_lector_debil_cae_en_percentil_bajo():
    r = percentil_nivel_lector(_items(9, 30), grado=2, edad=7)
    assert r is not None
    assert r["percentil_por_grado"] <= 10, r


def test_un_lector_solido_cae_en_percentil_alto():
    r = percentil_nivel_lector(_items(29, 30), grado=2, edad=7)
    assert r["percentil_por_grado"] >= 80, r


def test_el_puntaje_se_lleva_a_la_escala_de_100_del_baremo():
    """El baremo está calibrado sobre los 100 ítems del subtest. Pasarle 9
    sobre 30 sin escalar lo leería como 9 sobre 100 y daría un percentil
    catastrófico para un alumno que respondió el 30 %."""
    r = percentil_nivel_lector(_items(9, 30), grado=2)
    assert r["puntaje_escala_tede"] == 30
    assert r["escalado"] is True


def test_una_administracion_completa_no_se_escala():
    r = percentil_nivel_lector(_items(70, 100), grado=2)
    assert r["escalado"] is False
    assert r["puntaje_escala_tede"] == 70


def test_sin_items_de_lectura_no_hay_percentil():
    """Preferible no informar percentil a informar uno sin fundamento."""
    assert percentil_nivel_lector(_items(5, 10, modulo="dictado"), grado=2) is None
    assert percentil_nivel_lector([], grado=2) is None


def test_la_edad_y_el_grado_dan_tablas_distintas():
    """Un repetidor de 9 años en 2º no se compara igual contra su curso que
    contra su edad, y el TEDE tiene una tabla para cada cosa."""
    r = percentil_nivel_lector(_items(24, 30), grado=2, edad=9)
    assert "percentil_por_grado" in r and "percentil_por_edad" in r
    assert r["percentil_por_grado"] != r["percentil_por_edad"]


def test_solo_se_calcula_nivel_lector():
    """El TEDE tiene un segundo subtest, Errores Específicos, que puntúa sobre
    71 ítems fijos restando errores. Nuestro conteo de errores no corresponde a
    esa escala, así que llevarlo a esa tabla daría un número con apariencia
    normativa y sin fundamento."""
    r = percentil_nivel_lector(_items(20, 30), grado=2)
    assert r["subtest"] == "nivel_lector"
    assert "errores_especificos" not in r


def test_se_informa_de_cuantos_items_sale():
    """Quien lea el percentil necesita saber cuánta confianza darle: no es lo
    mismo derivarlo de 100 ítems que de 30."""
    r = percentil_nivel_lector(_items(20, 30), grado=2)
    assert r["items_administrados"] == 30
    assert r["aciertos"] == 20
    assert "TEDE" in r["fuente"]


def test_la_tabla_cubre_los_grados_del_instrumento():
    # El TEDE se estandarizó de 1º a 5º básico.
    for grado in (1, 2, 3, 4, 5):
        assert tede_percentil(50, "nivel_lector", grado=grado)


# ─── Segundo subtest: Errores Específicos ────────────────────────────────────
# La primera lectura del instrumento llevó a NO conectar este baremo, razonando
# que nuestros códigos de error (INV, SUS, OMI, ROT) no corresponden a sus 71
# ítems. El razonamiento era correcto y la conclusión no: no había que mapear
# los códigos, sino reconocer que los 71 ítems ya estaban en el banco bajo los
# prefijos M05_CS, GS, IL, IP, LW y OS.

from app.tede_scoring import (
    GRUPOS_ERRORES_ESPECIFICOS,
    TOTAL_ERRORES_ESPECIFICOS,
    percentil_errores_especificos,
)


def _items_ee(aciertos: int, total: int):
    grupos = list(GRUPOS_ERRORES_ESPECIFICOS)
    return [
        {"item_code": f"{grupos[i % len(grupos)]}_{i:03d}", "is_correct": i < aciertos}
        for i in range(total)
    ]


def test_los_seis_grupos_suman_los_items_del_instrumento():
    """El TEDE declara 71 ítems en este subtest y el banco tiene exactamente
    esa cantidad repartida en los seis grupos."""
    assert len(GRUPOS_ERRORES_ESPECIFICOS) == 6
    assert TOTAL_ERRORES_ESPECIFICOS == 71


def test_puntua_aciertos_menos_errores():
    """Es la diferencia con Nivel Lector, donde no se restan las incorrectas.
    Aquí el instrumento dice explícitamente: aciertos - errores = puntaje."""
    r = percentil_errores_especificos(_items_ee(50, 71), grado=3)
    assert r["aciertos"] == 50
    assert r["errores"] == 21
    assert r["puntaje_escala_tede"] == 29


def test_muchos_errores_dan_percentil_bajo():
    r = percentil_errores_especificos(_items_ee(12, 36), grado=3, edad=8)
    assert r["percentil_por_grado"] <= 10


def test_casi_sin_errores_da_percentil_alto():
    r = percentil_errores_especificos(_items_ee(35, 36), grado=3, edad=8)
    assert r["percentil_por_grado"] >= 40


def test_el_puntaje_no_baja_de_cero():
    """El instrumento no contempla negativos: quien falla más de lo que
    acierta queda en el piso de la tabla, no fuera de ella."""
    r = percentil_errores_especificos(_items_ee(2, 36), grado=3)
    assert r["puntaje_escala_tede"] == 0
    assert r["percentil_por_grado"] >= 1


def test_sin_items_del_subtest_no_hay_percentil():
    otros = [{"item_code": "M03_SL_001", "is_correct": True}]
    assert percentil_errores_especificos(otros, grado=3) is None
    assert percentil_errores_especificos([], grado=3) is None


def test_los_dos_subtests_son_independientes():
    """Nivel Lector y Errores Específicos tienen tablas distintas y se
    calculan por separado, como indica el instrumento."""
    items = _items_ee(30, 36) + [
        {"module": "lectura_voz_alta", "is_correct": True, "item_code": "M03_SL_001"}
        for _ in range(20)
    ]
    ee = percentil_errores_especificos(items, grado=3)
    nl = percentil_nivel_lector(items, grado=3)
    assert ee["subtest"] == "errores_especificos"
    assert nl["subtest"] == "nivel_lector"
    assert ee["items_administrados"] != nl["items_administrados"]
