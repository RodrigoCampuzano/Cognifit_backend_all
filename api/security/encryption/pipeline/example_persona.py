"""Entidad de ejemplo del pizarrón. Muestra el marcado declarativo @sensible.

Campos sensibles (cifrados en reposo) vs. no sensibles (en claro), tal como en
el diagrama de clase: Nombres/Apellidos/NSS se cifran; Edad/Rol Familiar no.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from security.encryption.pipeline.decorators import sensitive


@dataclass(slots=True)
class Persona:
    nombres: str = cast(str, sensitive())
    apellidos: str = cast(str, sensitive())
    nss: str = cast(str, sensitive())
    fecha_nacimiento: str = cast(str, sensitive())
    edad: int | None = None            # no sensible
    rol_familiar: str | None = None    # no sensible
    id: int | None = None
