# CogniFit Backend FastAPI

API segura para CogniFit Escolar: deteccion temprana de riesgo de dislexia, bateria Flutter, pipeline PLN/ML, rutas adaptativas, seguimiento y reportes.

## Que incluye

- FastAPI con Swagger en `/docs` y Redoc en `/redoc`.
- JWT access/refresh tokens, hashes Argon2 para contrasenas y revocacion de refresh tokens.
- RBAC por roles `ADMIN`, `SPECIALIST`, `TEACHER`, `PARENT`, `STUDENT`.
- Middlewares OWASP: rate limiting, headers de seguridad, CORS cerrado por entorno, logs con redaccion de secretos.
- Repositorios PostgreSQL integrados al schema `auth`, `academic`, `assessment`, `diagnosis`, `intervention`, `tracking`, `reporting`, `audit`.
- Pipeline PLN deterministic fallback: normalizacion, distancia de edicion, errores OMI/SUS/INV/ROT/LEX/SEG/UNI/FON/ADD/LEN/COM/ACC, similitud fonetica y n-gramas.
- Clasificador inicial rule-based listo para reemplazar por `RandomForest`/`SVM` entrenado con `joblib`.
- Verificador de integracion DB: `scripts/verify_db_integration.py`.

> Nota clinica: la API emite estimaciones de riesgo y apoyo docente. No sustituye diagnostico clinico ni valoracion especializada.

## Arranque rapido con Docker

```powershell
cd outputs\cognifit_backend
Copy-Item .env.development .env
docker compose up --build
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

El `docker-compose.yml` inicializa PostgreSQL con `infrastructure/database/migrations/001_cognifit_schema_v2_full.sql`.

## Arranque local

```powershell
cd outputs\cognifit_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.development .env
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Verificar integracion con DB

```powershell
python scripts\verify_db_integration.py --database-url "postgresql://cognifit_api:cognifit_api_dev_password@localhost:5432/cognifit"
```

El verificador revisa schemas, tablas, vistas, columnas criticas y semillas minimas:

- `assessment.v_battery_catalog` con 9 modulos.
- `assessment.teacher_screening_items` con 8 preguntas.
- `diagnosis.feature_definitions` con 28 features.
- `diagnosis.error_codes`.
- `intervention.route_templates`.
- `audit.audit_log`.

## Flujo implementado

1. Docente responde PRODISLEX digitalizado (`/screening/teacher-results`).
2. API calcula score 0-100 y decide `QUICK` o `FULL`.
3. API asigna modulos segun score (`/screening/assignments`).
4. App Flutter abre sesiones y envia respuestas (`/screening/sessions/{id}/responses`).
5. Pipeline PLN analiza respuesta por item, guarda eventos de error y vector 28D.
6. Diagnostico probabilistico genera subtipo, severidad, riesgo y ruta adaptativa.
7. Seguimiento acumula serie temporal y dispara alertas de estancamiento.

## Seguridad aplicada

- OWASP API1: RBAC por endpoint y RLS preparado en PostgreSQL.
- OWASP API2: Argon2id, JWT con expiracion corta, refresh token hasheado y revocable.
- OWASP API3: PII cifrada via `pgcrypto`; helpers Fernet para campos fuera de DB.
- OWASP API4: rate limiting por IP y ruta.
- OWASP API7/API8: configuracion por entorno, CORS explicito, headers de seguridad.
- OWASP API10: auditoria append-only y logs sin contrasenas/tokens.

Para produccion cambia todos los secretos de `.env.production`, fuerza HTTPS en el proxy, usa una clave KMS/Secrets Manager y ejecuta backups/restores probados.
