"""Guardián anti-divergencia entre las reglas del cliente y las del servidor.

La validación del cliente es un espejo de la del servidor. Si alguien cambia
una restricción en Pydantic y no la actualiza en Dart, aparece el peor de los
dos mundos: la app dice que el dato está bien y el servidor lo rechaza con un
422 —o al revés, el cliente bloquea algo que el servidor aceptaría.

Esta prueba lee el archivo de Dart y comprueba que las constantes coincidan.
No es elegante, pero es la única forma de que la divergencia falle en CI en
lugar de descubrirse en una escuela sin señal.
"""
import re
from pathlib import Path

import pytest

from api.v1.auth.schemas import RegisterUserRequest

# El cliente y el API viven en repos separados, así que el archivo puede no
# estar montado (p. ej. dentro del contenedor del API). En ese caso la prueba
# se salta en vez de fallar: se busca en varias ubicaciones conocidas.
_CANDIDATOS = [
    Path(__file__).resolve().parents[2].parent
    / "app/cognifit_mobile/lib/core/validation/input_rules.dart",
    Path("/client/lib/core/validation/input_rules.dart"),
]
REGLAS_DART = next((p for p in _CANDIDATOS if p.exists()), _CANDIDATOS[0])


def _texto_dart() -> str:
    if not REGLAS_DART.exists():
        pytest.skip(
            "input_rules.dart no está disponible en este entorno; "
            "el guardián corre donde ambos repos son visibles"
        )
    return REGLAS_DART.read_text(encoding="utf-8")


def _constante_dart(nombre: str) -> int:
    texto = _texto_dart()
    m = re.search(rf"static const int {nombre}\s*=\s*(\d+);", texto)
    assert m, f"No se encontró la constante {nombre} en input_rules.dart"
    return int(m.group(1))


def _restriccion(modelo, campo: str, clave: str) -> int:
    meta = modelo.model_fields[campo].metadata
    for m in meta:
        if hasattr(m, clave):
            return getattr(m, clave)
    raise AssertionError(f"{campo} no declara {clave}")


def test_password_minimo_de_registro_coincide():
    assert _constante_dart("passwordMinRegistro") == _restriccion(
        RegisterUserRequest, "password", "min_length"
    )


def test_password_maximo_coincide():
    assert _constante_dart("passwordMax") == _restriccion(
        RegisterUserRequest, "password", "max_length"
    )


def test_el_cliente_no_exige_minimo_al_iniciar_sesion():
    """`LoginRequest.password` no declara longitud mínima a propósito: las
    cuentas creadas por el registro de institución usan la regla de 8, y
    exigir 12 en la pantalla de acceso las dejaría fuera."""
    from api.v1.auth.schemas import LoginRequest

    assert not LoginRequest.model_fields["password"].metadata, (
        "Si se agrega un mínimo a LoginRequest hay que revisar "
        "Validators.passwordAcceso en el cliente"
    )

    texto = _texto_dart()
    bloque = texto.split("passwordAcceso")[1].split("static String?")[0]
    assert "length <" not in bloque, (
        "passwordAcceso no debe comprobar longitud: seria mas estricto "
        "que el servidor"
    )
