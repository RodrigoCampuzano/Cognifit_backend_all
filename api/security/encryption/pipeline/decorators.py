"""Marcador declarativo de campos sensibles (el "@Sensible" del pizarrón).

Se apoya en `dataclasses.field(metadata=...)` para anotar qué atributos deben
cifrarse, sin acoplar el dominio al motor criptográfico.
"""
from __future__ import annotations

from dataclasses import MISSING, Field, field
from typing import Callable, cast

_MARK = {"sensitive": True}


def sensitive(*, default: object = MISSING, default_factory: object = MISSING) -> Field[object]:
    """Marca un atributo de dataclass como sensible (se cifrará en reposo).

    Uso:
        @dataclass
        class Persona:
            nombres: str = cast(str, sensitive())
            edad: int          # no sensible → se persiste en claro
    """
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("Usa default o default_factory, no ambos.")
    if default is not MISSING:
        return cast(Field[object], field(default=default, metadata=_MARK))
    if default_factory is not MISSING:
        if not callable(default_factory):
            raise TypeError("default_factory debe ser invocable.")
        return cast(Field[object], field(default_factory=cast(Callable[[], object], default_factory), metadata=_MARK))
    return cast(Field[object], field(metadata=_MARK))
