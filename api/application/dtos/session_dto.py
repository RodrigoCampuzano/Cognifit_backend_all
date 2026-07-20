from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from uuid import UUID


class StartSessionDto(BaseModel):
    assignment_id: UUID
    module_code: str = Field(min_length=3, max_length=64)
    device_id: str | None = Field(default=None, max_length=120)
    app_version: str | None = Field(default=None, max_length=40)


class TimingDetailDto(BaseModel):
    """Desglose de `response_time_ms`.

    Era un `dict` libre: el único campo del API que aceptaba cualquier
    estructura y la guardaba tal cual como JSONB. No es explotable —exige
    autenticación y pasa por la verificación de propiedad, y se almacena sin
    ejecutarse— pero un campo sin forma no se puede consultar con confianza
    después, y estos valores son la base del reentrenamiento del modelo.

    `extra="forbid"` rechaza claves desconocidas en lugar de guardarlas en
    silencio: si una versión nueva de la app empieza a mandar un campo que el
    servidor no conoce, conviene enterarse con un 422 y no descubrirlo meses
    después al entrenar.
    """

    model_config = {"extra": "forbid"}

    # Los cuatro tiempos comparten el mismo techo que response_time_ms: cinco
    # minutos por ítem no es un dato lento, es un dato roto.
    total_ms: int | None = Field(default=None, ge=0, le=300000)
    tts_ms: int | None = Field(default=None, ge=0, le=300000)
    background_ms: int | None = Field(default=None, ge=0, le=300000)
    net_ms: int | None = Field(default=None, ge=0, le=300000)

    stimulus_chars: int | None = Field(default=None, ge=0, le=10000)
    stimulus_words: int | None = Field(default=None, ge=0, le=2000)
    difficulty: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def _coherencia_de_tiempos(self) -> "TimingDetailDto":
        """El neto es lo que queda tras descontar audio y segundo plano, así
        que no puede superar al total. Un neto mayor significa que el cliente
        midió mal, y ese número alimenta el 36 % de la decisión del modelo:
        conviene rechazarlo, no promediarlo con los buenos."""
        if self.net_ms is not None and self.total_ms is not None:
            if self.net_ms > self.total_ms:
                raise ValueError(
                    f"net_ms ({self.net_ms}) no puede superar a total_ms ({self.total_ms})"
                )
        return self


class ResponseDto(BaseModel):
    item_id: UUID
    raw_response: str | None = Field(default=None, max_length=2000)
    response_time_ms: int | None = Field(default=None, ge=0, le=300000)
    capture_modality: str | None = Field(default=None, max_length=40)
    response_audio_url: str | None = Field(default=None, max_length=2000)
    stt_confidence: float | None = Field(default=None, ge=0, le=1)
    # Opcional para no romper clientes viejos; se persiste para auditar de
    # dónde salió el tiempo y para alimentar mejores métricas en un
    # reentrenamiento futuro.
    timing_detail: TimingDetailDto | None = Field(default=None)
