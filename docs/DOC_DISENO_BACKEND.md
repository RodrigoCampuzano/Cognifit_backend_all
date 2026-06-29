# Diseño del Backend — Implementación ↔ Patrón ↔ Requerimiento (Entregable #1)

Respalda el avance de **API y Base de Datos** con las decisiones de diseño y los
patrones aplicados, enlazado a la tabla de trazabilidad (ADR) y a las Historias de
Usuario (HU). Ámbito: parte de Rodrigo (Backend SOA / BD).

## 1. Arquitectura general

Backend **FastAPI** con arquitectura **hexagonal / por capas**:

- **API** (`api/api/v1/*`): routers por dominio + inyección de dependencias + middleware.
- **Aplicación** (`application/use_cases`, `application/services`): orquestación (Commands) y servicios.
- **Dominio** (`domain/`): *ports* (interfaces), entidades y *value objects*.
- **Infraestructura** (`infrastructure/`): repositorios PostgreSQL, clientes de los
  microservicios PLN, seguridad (JWT, Argon2, pipeline de cifrado, auditoría), Redis.

Diagramas: ver [DISENO_API.md](DISENO_API.md).

## 2. Mapa Implementación ↔ Patrón ↔ ADR/HU

| Implementación (archivo/módulo) | Patrón | ADR / HU |
|---|---|---|
| `dependencies/auth.py` (`get_current_user`, JWT) | **Proxy** de autenticación | ADR-15 / HU-BK-01 |
| App FastAPI + prefijo `/api/v1` + middleware | **Gateway** (punto de entrada único) | ADR-16 / HU-BK-02 |
| `UserRepository`, `admin/router.py` (CRUD) | **Repository** | ADR-17 / HU-BK-03 |
| `pg_student_repository.py` (consulta por grupo/grado) | **Query Object** | ADR-18 / HU-BK-04 |
| Use cases `SubmitAnswersUseCase`, `GetResultUseCase` | **Command** | ADR-19 / HU-BK-05 |
| `pg_tracking_repository.py` (`evaluate_progress`, alertas) | **Observer** | ADR-20 / HU-BK-09 |
| `GenerateReportUseCase` (ReportLab) | **Builder** | ADR-21 / HU-BK-10 |
| `infrastructure/cache` (Redis) | **Decorator** de cache | ADR-22 / HU-BK-11 |
| `health.py` (`/health`, `/health/db`, `/health/pln`) | **Singleton** / registro de salud | ADR-23 / HU-BK-12 |
| `PgModelVersionRepository.activate` (estados del modelo) | **State** | ADR-24 / HU-BK-13 |
| `security/audit/audit_logger.py` (append-only) | **Decorator** de auditoría | ADR-25 / HU-BK-14 |
| `UserRepository` (usuarios + roles) | **Repository** | ADR-26 / HU-BD-01 |
| `get_db()` (transacción por request) | **Unit of Work** | ADR-27 / HU-BD-03 |
| `DiagnosisServiceClient` / `RecommendationServiceClient` | **Facade / Adapter** a microservicios | (consume ADR-12/13) |
| `dependencies/services.py` (`@lru_cache`) | **Singleton** de clientes/config | — |
| `application/dtos/*`, schemas Pydantic | **DTO** | ADR-10 / HU-MD-10 |
| `security/encryption/pipeline/*` (AES-GCM) | **Pipe & Filters / Chain** | HU-BD-11 |

## 3. Modelo de datos (BD) y HU cubiertas

PostgreSQL con schemas por dominio: `auth, academic, assessment, diagnosis,
intervention, tracking, reporting, audit`. Cobertura:

| HU-BD | Implementación |
|---|---|
| HU-BD-01 Usuarios y roles | `auth.users` (Argon2, correo único, rol catálogo) |
| HU-BD-02 Estructura escolar | `academic.schools/groups/students` (FK, borrado lógico) |
| HU-BD-03 Tests y respuestas originales | `assessment.tests/test_items/test_sessions/student_responses` |
| HU-BD-04 Persistencia del diagnóstico | `diagnosis.diagnoses` (subtipo, severidad, riesgo, confianza) |
| HU-BD-05/06 Banco de ejercicios y rutas | `intervention.exercises/route_templates/student_paths` |
| HU-BD-07 Series temporales | `tracking.diagnosis_ml_sessions` |
| HU-BD-08 Alertas | `tracking.alerts` |
| HU-BD-09 Reportes | `reporting.report_requests` |
| HU-BD-10 Versiones de modelo + auditoría | `diagnosis.ml_model_versions`, `audit.audit_log` (append-only) |
| HU-BD-11 Protección de datos de menores | `pgcrypto` (full_name) + **pipeline de cifrado AES-GCM** (app-side) + RLS + consentimiento |

Migraciones: `schema.sql → 002 → 003 → 004 → 005` (ver `deploy/`).

## 4. Seguridad (OWASP)

- **RBAC** por rol (`require_roles`); **RLS** preparado (`app.current_user_id/role`).
- **JWT** access corto + refresh revocable; **Argon2id** para contraseñas.
- **Cifrado de PII**: pgcrypto en BD + pipeline AES-GCM en aplicación (HU-BD-11).
- **Auditoría** append-only; **rate limiting**; cabeceras de seguridad (CSP, HSTS, etc.).

## 5. Integración con microservicios ML (Carlos)

El backend consume Diagnosis (8001) y Recommendation (8002) vía clientes con
**fallback local** si no responden (`PLN_FALLBACK_ENABLED`). Contrato y flujo en
`docs/flujo_completo.md` y `Pln/integracion_rodrigo.md`.

## 6. Estado de avance

- API: 9 dominios de endpoints implementados y desplegados (Railway + Neon).
- Flujo de test de punta a punta operativo (sesión → ítems → respuestas → diagnóstico → ruta).
- Cifrado de datos sensibles (patrón de clase) implementado y probado — ver
  [CIFRADO_DATOS_SENSIBLES.md](CIFRADO_DATOS_SENSIBLES.md).
- 40 requerimientos proyectados en la tabla de trazabilidad (entregable #3).
