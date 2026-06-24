from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.development"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "staging", "production"] = "development"
    project_name: str = "CogniFit Escolar API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    enable_swagger: bool = True
    allow_public_registration: bool = False

    database_url: str = Field(..., min_length=10)
    sync_database_url: str | None = None
    db_encryption_key: str = Field(..., min_length=8)
    redis_url: str | None = None

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_pepper: str = ""

    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 2

    field_encryption_key: str | None = None
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    log_level: str = "INFO"

    # Microservicios PLN (modelos entrenados). En Docker apuntar a los nombres del compose.
    diagnosis_service_url: str = "http://localhost:8001"
    recommendation_service_url: str = "http://localhost:8002"
    pln_timeout_seconds: float = 10.0
    pln_retries: int = 1            # reintentos ante 503 (modelos cargando)
    pln_fallback_enabled: bool = True  # usar pipeline local si el servicio no responde

    reports_dir: str = "reports_storage"  # almacenamiento local de PDFs generados (HU-BK-10)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
