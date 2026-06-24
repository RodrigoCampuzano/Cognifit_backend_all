from __future__ import annotations


class PlnServiceError(Exception):
    """El microservicio PLN no pudo atender la petición (timeout/5xx/conexión)."""

    def __init__(self, service: str, detail: str, status_code: int | None = None) -> None:
        self.service = service
        self.detail = detail
        self.status_code = status_code
        super().__init__(f"[{service}] {detail}")
