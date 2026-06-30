from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from api.middleware.auth_middleware import AuthContextMiddleware
from api.middleware.logging_middleware import RequestLoggingMiddleware
from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.middleware.security_headers import SecurityHeadersMiddleware
from api.v1.auth.router import router as auth_router
from api.v1.admin.router import router as admin_router
from api.v1.groups.router import router as groups_router
from api.v1.health import router as health_router
from api.v1.intervention.router import router as intervention_router
from api.v1.reports.router import router as reports_router
from api.v1.tracking.router import router as tracking_router
from api.v1.screening.router import router as screening_router
from api.v1.security.router import router as security_router
from api.v1.students.router import router as students_router
from config.logging import setup_logging
from config.settings import get_settings
from domain.exceptions.domain_exception import DomainException

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="API segura para screening, pipeline PLN/ML, rutas adaptativas y seguimiento CogniFit Escolar.",
    docs_url=None,   # Swagger UI deshabilitado: la referencia interactiva se sirve con Scalar (ver /docs).
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_swagger else None,
)


def _scalar_html() -> str:
    """Referencia de API interactiva con Scalar (reemplaza Swagger UI).
    El bundle se carga desde cdn.jsdelivr.net, ya permitido por la CSP en /docs."""
    return f"""<!doctype html>
<html>
  <head>
    <title>{settings.project_name} — API Reference</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" href="data:," />
  </head>
  <body>
    <script id="api-reference" data-url="{app.openapi_url}"></script>
    <script>
      var configuration = {{ theme: 'purple', layout: 'modern', hideDownloadButton: false }};
      document.getElementById('api-reference').dataset.configuration = JSON.stringify(configuration);
    </script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>"""


if settings.enable_swagger:
    @app.get("/docs", include_in_schema=False)
    async def scalar_reference() -> HTMLResponse:  # noqa: D401
        return HTMLResponse(_scalar_html())

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(groups_router, prefix=settings.api_v1_prefix)
app.include_router(students_router, prefix=settings.api_v1_prefix)
app.include_router(screening_router, prefix=settings.api_v1_prefix)
app.include_router(intervention_router, prefix=settings.api_v1_prefix)
app.include_router(tracking_router, prefix=settings.api_v1_prefix)
app.include_router(reports_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(security_router, prefix=settings.api_v1_prefix)


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc), "code": exc.code})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
