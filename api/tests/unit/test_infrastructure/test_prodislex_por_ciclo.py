"""PRODISLEX publica un protocolo por ciclo y sus indicadores difieren.

No es una variación menor: en 1º se busca si el niño ESTÁ ADQUIRIENDO la
lectura —segmentar y unir sonidos— y en 3er ciclo si la AUTOMATIZÓ, con la
velocidad comparada contra la edad cronológica en vez de contra el grupo, y
con el uso de la lectura para estudiar.

La aplicación usaba los mismos ítems para un niño de 6 años y uno de 12: le
preguntaba al de 1º si toma bien apuntes. Como el objetivo es seguir el avance
en el tiempo, aplicar el mismo instrumento a los 6 y a los 12 mide cosas
distintas con la misma vara.
"""
import inspect

import pytest

from infrastructure.database.repositories.pg_session_repository import PgSessionRepository


@pytest.mark.parametrize(
    "grado,ciclo",
    [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3)],
)
def test_el_grado_cae_en_el_ciclo_correcto(grado, ciclo):
    assert PgSessionRepository.ciclo_de_grado(grado) == ciclo


def test_sin_grado_se_usa_el_primer_ciclo():
    """Es el conjunto más chico y el que menos supone. Equivocarse hacia abajo
    es menos dañino que preguntarle a un niño de 1º por toma de apuntes."""
    assert PgSessionRepository.ciclo_de_grado(None) == 1
    assert PgSessionRepository.ciclo_de_grado(0) == 1


def test_un_grado_fuera_de_rango_no_rompe():
    assert PgSessionRepository.ciclo_de_grado(9) == 3


def test_la_consulta_filtra_por_ciclo():
    sql = inspect.getsource(PgSessionRepository.get_teacher_items)
    assert ":ciclo = ANY(ciclos)" in sql, (
        "sin filtro todos los grados reciben el mismo cuestionario"
    )


def test_el_grado_entra_en_la_clave_de_cache():
    """La clave era solo el namespace, así que los tres ciclos habrían
    compartido una respuesta: el primero en pedirla definía la de todos."""
    from api.v1.screening import router as mod

    fuente = inspect.getsource(mod)
    i = fuente.index("screening_teacher_items")
    assert "key_params" in fuente[i - 120 : i + 120]


def test_el_decorador_incluye_los_parametros_en_la_clave():
    from infrastructure.cache.cache_decorator import cached_endpoint

    firma = inspect.signature(cached_endpoint)
    assert "key_params" in firma.parameters
