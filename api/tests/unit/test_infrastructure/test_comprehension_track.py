"""La vía de comprensión se entrega por grado, y el grado lo decide el
servidor. Estas pruebas fijan esa propiedad: si alguien la relaja aceptando el
grado del cliente, la verificación de propiedad deja de servir para nada."""
import asyncio
import inspect

import pytest


def test_el_endpoint_no_acepta_el_grado_del_cliente():
    # Si apareciera un parámetro `grade`, cualquiera podría pedir material de
    # otro grado y sondear grados ajenos sin pasar por la verificación.
    from api.v1.intervention.router import comprehension_track

    params = set(inspect.signature(comprehension_track).parameters)
    assert "grade" not in params
    assert "student_id" in params, "el grado se deriva del alumno"


def test_el_endpoint_verifica_propiedad_antes_de_consultar():
    """El orden importa: primero se comprueba la propiedad, después se lee el
    grado. Al revés, un 409 por 'sin grado asignado' revelaría la existencia de
    un alumno ajeno."""
    from api.v1.intervention import router as mod

    fuente = inspect.getsource(mod.comprehension_track)
    pos_ownership = fuente.index("_verify_student_ownership")
    pos_query = fuente.index("academic.students")
    assert pos_ownership < pos_query


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    # `_get_client()` descarta el cliente si está cerrado; sin este atributo el
    # doble se reemplaza por un httpx real y la prueba sale a la red.
    is_closed = False

    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.paths: list[str] = []

    async def get(self, path: str) -> _FakeResponse:
        self.paths.append(path)
        return self.response


def test_cliente_pide_el_grado_correcto():
    from infrastructure.pln.recommendation_client import RecommendationServiceClient

    client = RecommendationServiceClient("http://recommendation:8002")
    fake = _FakeHttpClient(_FakeResponse(200, {"grade": "6", "total": 7}))
    client._client = fake

    data = asyncio.run(client.comprehension_track("6"))

    assert fake.paths == ["/comprehension/6"]
    assert data["total"] == 7


def test_grado_vacio_no_es_error():
    """Un grado sin contenido responde 200 con lista vacía. Convertirlo en
    excepción obligaría al cliente a distinguir 'todavía no hay material' de
    'el servicio se cayó', que son cosas muy distintas."""
    from infrastructure.pln.recommendation_client import RecommendationServiceClient

    client = RecommendationServiceClient("http://recommendation:8002")
    client._client = _FakeHttpClient(
        _FakeResponse(200, {"grade": "1", "total": 0, "exercises": []})
    )

    data = asyncio.run(client.comprehension_track("1"))
    assert data["total"] == 0


def test_error_del_servicio_si_se_propaga():
    from infrastructure.pln.recommendation_client import RecommendationServiceClient
    from infrastructure.pln.errors import PlnServiceError

    client = RecommendationServiceClient("http://recommendation:8002")
    client._client = _FakeHttpClient(_FakeResponse(500, {"detail": "boom"}))

    with pytest.raises(PlnServiceError):
        asyncio.run(client.comprehension_track("6"))
