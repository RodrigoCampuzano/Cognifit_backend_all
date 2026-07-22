from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
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

    # Notificaciones por correo (SMTP estándar). Si smtp_host es None, el envío
    # se omite silenciosamente (ver infrastructure/email/smtp_email_service.py).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    notification_email_to: str | None = None  # a dónde avisar altas de institución nuevas

    # Pagos de licencia (Conekta). Si conekta_private_key es None, los
    # endpoints de checkout responden 503 en vez de fallar de forma opaca
    # contra la API de Conekta (ver infrastructure/conekta/conekta_client.py).
    conekta_private_key: str | None = None
    conekta_public_key: str | None = None
    conekta_webhook_secret: str | None = None
    conekta_api_version: str = "2.1.0"
    conekta_base_url: str = "https://api.conekta.io"

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

    @model_validator(mode="after")
    def _check_pln_urls_in_production(self) -> "Settings":
        """En producción, dejar las URLs del PLN en localhost es casi seguro un
        despliegue mal configurado: el contenedor no tiene nada escuchando ahí,
        así que cada diagnóstico degradaría en silencio al fallback local (o
        fallaría) en vez de usar los modelos entrenados. A diferencia de
        database_url/jwt_secret_key, estos campos tienen default, así que la
        app arrancaba feliz y el problema recién aparecía en el primer
        diagnóstico. Mejor fallar al arrancar.
        """
        if not self.is_production:
            return self
        locales = [
            name
            for name, url in (
                ("DIAGNOSIS_SERVICE_URL", self.diagnosis_service_url),
                ("RECOMMENDATION_SERVICE_URL", self.recommendation_service_url),
            )
            if "localhost" in url or "127.0.0.1" in url
        ]
        if locales:
            raise ValueError(
                f"APP_ENV=production pero {', '.join(locales)} apunta(n) a localhost. "
                "Configura las URLs internas de los microservicios PLN."
            )
        return self

    @model_validator(mode="after")
    def _check_conekta_keys_in_production(self) -> "Settings":
        """A diferencia de SMTP (best-effort, se omite si falta), un checkout de
        pago sin llaves de Conekta configuradas no puede degradarse en
        silencio: el endpoint fallaría igual, solo que en el primer intento de
        cobro real de una escuela en vez de al arrancar. Mejor fallar temprano."""
        if not self.is_production:
            return self
        faltantes = [
            name
            for name, value in (
                ("CONEKTA_PRIVATE_KEY", self.conekta_private_key),
                ("CONEKTA_PUBLIC_KEY", self.conekta_public_key),
                ("CONEKTA_WEBHOOK_SECRET", self.conekta_webhook_secret),
            )
            if not value
        ]
        if faltantes:
            raise ValueError(
                f"APP_ENV=production pero falta(n) {', '.join(faltantes)}. "
                "Configura las llaves de Conekta antes de desplegar."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
