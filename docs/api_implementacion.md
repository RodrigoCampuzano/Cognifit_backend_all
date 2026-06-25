# Implementacion API CogniFit Backend

Entregable: `outputs/cognifit_backend`

## Base tecnica

- Framework: FastAPI.
- Documentacion Swagger: `/docs`.
- Versionado: `/api/v1`.
- DB: PostgreSQL con schemas `auth`, `academic`, `assessment`, `diagnosis`, `intervention`, `tracking`, `reporting`, `audit`.
- Hash de contrasenas: Argon2id via `argon2-cffi`.
- Tokens: JWT access token corto + refresh token hasheado y revocable.
- Pipeline PLN: normalizacion, distancia de edicion, errores OMI/SUS/INV/ROT/LEX/SEG/UNI/FON/ADD/LEN/COM/ACC, similitud fonetica, n-gramas y vector 28D.

## Endpoints principales

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/token`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/students`
- `POST /api/v1/students`
- `GET /api/v1/students/{student_id}`
- `GET /api/v1/screening/catalog`
- `GET /api/v1/screening/teacher-items`
- `POST /api/v1/screening/teacher-results`
- `POST /api/v1/screening/assignments`
- `POST /api/v1/screening/sessions`
- `GET /api/v1/screening/sessions/{session_id}/items`
- `POST /api/v1/screening/sessions/{session_id}/responses`
- `POST /api/v1/screening/sessions/{session_id}/diagnose`
- `GET /api/v1/screening/students/{student_id}/latest-risk`
- `POST /api/v1/reports`
- `GET /api/v1/reports/students/{student_id}/payload`
- `GET /api/v1/security/controls`
- `POST /api/v1/security/audit`
- `POST /api/v1/security/remote-wipe`

## Integracion DB

- Schema completo para ambientes nuevos:
  `infrastructure/database/migrations/001_cognifit_schema_v2_full.sql`
- Migracion para DB existente:
  `infrastructure/database/migrations/002_cognifit_integration_migration_existing_db.sql`
- Verificador:
  `python scripts/verify_db_integration.py --database-url "postgresql://..."`

El verificador revisa schemas, tablas, vistas, columnas criticas y semillas minimas: 9 modulos, 8 preguntas docentes, 28 features, codigos de error y rutas de intervencion.

## Seguridad OWASP aplicada

- RBAC por rol y dependencias FastAPI.
- RLS preparado en PostgreSQL mediante contexto `app.current_user_id` y `app.current_user_role`.
- Rate limiting por IP/ruta.
- Cabeceras: CSP, HSTS en HTTPS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy y Permissions-Policy.
- PII cifrada en DB con `pgcrypto`; helper Fernet para campos fuera de DB.
- Auditoria append-only en `audit.audit_log`.
- Errores de autenticacion genericos para no filtrar informacion sensible.

## Validacion local realizada

- `python -m compileall -q outputs/cognifit_backend`: OK.
- `pytest`: no ejecutado porque el runtime local de Codex no trae `pytest` instalado. El proyecto incluye `pytest` en `requirements.txt`.
