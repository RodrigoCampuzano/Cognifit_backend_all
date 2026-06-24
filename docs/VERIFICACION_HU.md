# Verificación — MVP + Historias de Usuario vs Implementación

> Contraste de `docs/extracted_pdfs/mvp_cognifit_escolar.md` y `docs/HU COGNIFIT.pdf`
> (50 HU) contra el código de `api/`, la DB y los microservicios `Pln/` (no modificables,
> con modelos ya entrenados). Fecha: 2026-06-23.

Alcance: **HU-BD (BD)** y **HU-BK (Backend)** son el foco. **HU-MD (PLN/ML)** vive en
`Pln/` (ya entrenado). **HU-FL (Flutter, 14 HU)** queda **fuera de alcance**: no hay
código Flutter en el repo.

Leyenda: ✅ completo · ⚠️ parcial · ❌ falta.

## 1. Base de Datos (HU-BD) — 11/11 ✅

| HU | Tabla(s) | Estado |
|---|---|---|
| BD-01 usuarios y roles | `auth.users` (Argon2, rol enum, correo único) | ✅ |
| BD-02 escuelas/grupos/alumnos | `academic.schools/groups/students` (FK, borrado lógico) | ✅ |
| BD-03 tests + respuestas | `assessment.tests/test_sessions/student_responses` | ✅ |
| BD-04 diagnósticos | `diagnosis.diagnoses` (+ subtype/severity/risk_level + raw PLN 002) | ✅ |
| BD-05 banco de ejercicios | `intervention.exercises` (has_tts/has_stt, nivel, activo; 29 sincronizados en 003) | ✅ |
| BD-06 rutas de aprendizaje | `intervention.student_paths` (exercise_route, total, perfil, route_template 002) | ✅ |
| BD-07 historial de sesiones | `intervention.exercise_sessions` + `tracking.diagnosis_ml_sessions` | ✅ |
| BD-08 alertas | `tracking.alerts` (tipo, estado, urgencia, source_session) | ✅ |
| BD-09 reportes | `reporting.report_requests` | ✅ |
| BD-10 versiones modelo + logs | `diagnosis.ml_model_versions` + `audit.audit_log` | ✅ |
| BD-11 protección de menores | RLS, pgcrypto, consentimiento (`auth.guardian_consents`) | ✅ |

## 2. Backend — Microservicios FastAPI / SOA (HU-BK)

| HU | Estado | Evidencia / Gap |
|---|---|---|
| BK-01 auth JWT+Argon2 | ✅ | `/auth/register,login,token,refresh,logout,me` |
| BK-02 API Gateway | ⚠️ | El API FastAPI hace de gateway (valida JWT, rate-limit, base única, oculta PLN). SOA-lite aceptable para MVP; no es un gateway dedicado. |
| BK-03 gestión cuentas (admin CRUD todos los roles) | ✅ | **CERRADO.** `GET/POST/PATCH/DELETE /admin/users` (solo ADMIN, borrado lógico, sin correos duplicados). Requirió migración **004** que añade los roles `PARENT` y `SPECIALIST` al enum `auth.user_role` (001 solo traía ADMIN/TEACHER/STUDENT, pese a que el RBAC ya los usaba — bug encontrado en la verificación). |
| BK-04 alumnos por grupo/grado | ✅ | `/students` (GET/POST/{id}) con RBAC docente |
| BK-05 aplicación de tests | ✅ | `/screening/assignments,sessions,responses` y **dispara diagnóstico al cerrar** (`/sessions/{id}/diagnose`) |
| BK-06 microservicio diagnóstico | ✅ | `diagnosis_service` (8001) + el API lo invoca (modelos entrenados, `model_version` real) |
| BK-07 motor de recomendación | ✅ | `recommendation_service` (8002) + el API lo invoca y persiste la ruta |
| BK-08 ejercicios dinámicos | ✅ | `/intervention/next-exercise`, `/intervention/exercises/{id}`, `/active-path` |
| BK-09 seguimiento y alertas | ✅ | **CERRADO.** `/tracking/students/{id}/learning-curve`, `/metrics`, `/groups/{id}/metrics`, `/alerts`, `/alerts/{id}/read`, `/students/{id}/evaluate-progress` (genera alerta de estancamiento/recalibración deduplicada). Repo `pg_tracking_repository.py`. |
| BK-10 reportes PDF | ✅ | **CERRADO.** `POST /reports/{id}/generate` renderiza PDF con ReportLab → status READY; `GET /reports/{id}/download` entrega el archivo. |
| BK-11 caché Redis | ✅ | `infrastructure/cache/redis_client.py` |
| BK-12 monitoreo `/health` | ✅ | `/health/pln` agrega 8001+8002 (HU cumplida con la integración) |
| BK-13 gestión versiones modelo | ✅ | **CERRADO.** `GET /admin/model-versions`, `POST /admin/model-versions/activate` (la DB bloquea promover sin métricas vía `ck_model_production_thresholds`). |
| BK-14 logs y auditoría | ✅ | `audit.audit_log` + `/security/audit` (append-only) |

## 3. Minería de Datos / PLN-ML (HU-MD) — en `Pln/` (no modificable)

| HU | Estado | Dónde |
|---|---|---|
| MD-01 pipeline PLN caracteres/fonético | ✅ | `diagnosis_service/app/pln/*` |
| MD-02 TF-IDF / features | ✅ | `features.py` (vector 28D) |
| MD-03 clasificador subtipo+severidad | ✅ | `ml/predictor.py` (.pkl entrenados) |
| MD-04 validación/métricas | ✅ | `/model/info` |
| MD-05 dataset ruido disléxico | ✅ | notebook de entrenamiento (fuera de runtime) |
| MD-06 motor recomendación adaptativa | ✅ | `recommendation_service` |
| MD-07 series temporales | ⚠️ | `next-exercise` decide level_up/continue; falta el cálculo de curva en backend (ver BK-09) |
| MD-08 recalibración automática | ✅ | `recommendation_service /next-exercise` (>90% → level_up) |
| MD-09 alertas de estancamiento | ❌ | mismo gap que BK-09 (lado backend) |
| MD-10/11 métricas de evolución/rendimiento | ⚠️ | `/model/info` existe; falta endpoint agregado en el API |

## 4. Lo que cerró la integración PLN de esta sesión

BK-06, BK-07, BK-08, BK-12 + completitud de DB (migraciones 002 y 003). El diagnóstico
ahora usa los **modelos entrenados** (`model_version 20260618_0309`), la ruta proviene del
Recommendation Service y se persiste en `intervention.student_paths`, y los 29 ejercicios
referenciados por las 12 rutas existen en la DB.

## 5. Gaps cerrados (2026-06-23) — backend al nivel de las HU

Todos los gaps de §2 fueron implementados y verificados en runtime contra la DB:
BK-03, BK-09, BK-10, BK-13. Única migración nueva requerida: **004** (roles
`PARENT`/`SPECIALIST`). Detalle original de los gaps abajo (histórico).

1. **BK-09 / MD-07 / MD-09 — Seguimiento, curva y alertas** (Alta).
   - `GET /tracking/students/{id}/learning-curve` (errores/min, tiempos por sesión desde `diagnosis_ml_sessions`).
   - Generación de alerta de estancamiento (N sesiones sin mejora) → `tracking.alerts`; evitar duplicados.
   - `GET /tracking/students/{id}/metrics` y `GET /tracking/groups/{id}/metrics`.
   - `GET /tracking/alerts` (bandeja docente).
2. **BK-13 — Gestión de versiones de modelo** (Media).
   - `GET /admin/model-versions` (lista + métricas), `POST /admin/model-versions/{tag}/activate` (bloquea sin métricas validadas), registra en audit.
3. **BK-03 — CRUD admin de usuarios** (Media).
   - `GET/POST/PATCH/DELETE /admin/users` (borrado lógico, sin correos duplicados, solo ADMIN).
4. **BK-10 — Render real de PDF** (Media).
   - Integrar ReportLab en `GenerateReportUseCase` → archivo + status READY + descarga.

> Ninguno necesita cambios de esquema; `001+002+003` ya cubren las tablas. BK-10 podría
> requerir un campo de ruta de archivo si se persiste el binario (ya existe `report_requests`).
</content>
