# Verificación — MVP + Historias de Usuario vs Implementación

> Contraste de `docs/extracted_pdfs/mvp_cognifit_escolar.md` y `docs/HU COGNIFIT.pdf`
> (50 HU) contra el código de `api/`, la DB, los microservicios `Pln/` (no modificables,
> con modelos ya entrenados) y la app `app/cognifit_mobile/` (Flutter). Fecha: 2026-06-23,
> actualizado 2026-06-30 con la verificación de HU-FL.

Alcance: **HU-BD (BD)**, **HU-BK (Backend)** y **HU-FL (Flutter)** están cubiertas.
**HU-MD (PLN/ML)** vive en `Pln/` (ya entrenado, no modificable).

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

## 3. Frontend — App Móvil Flutter (HU-FL) — 8/14 ✅ · 3/14 ⚠️ · 3/14 ❌

Verificado en `app/cognifit_mobile/lib/` (repo git separado, gitignored en el repo
principal). El documento original marcaba este bloque "fuera de alcance" porque no
existía código Flutter; ahora sí existe y se contrasta a continuación.

| HU | Estado | Evidencia / Gap |
|---|---|---|
| FL-01 login seguro + bloqueo capturas | ⚠️ | JWT + sesión persistente OK (`auth_viewmodel.dart`, `token_storage.dart` vía `shared_preferences`, `api_client.dart` interceptor `Bearer`). **Falta `FLAG_SECURE`**: no hay `flutter_windowmanager` ni equivalente en `pubspec.yaml`/código — pantallas con datos clínicos no bloquean capturas de pantalla. |
| FL-02 alumnos por grupo/grado | ✅ | `students_screen.dart` + `students_viewmodel.dart` (búsqueda, alta/edición, estados de carga/error). |
| FL-03 asignación de test | ✅ | `tests_screen.dart`/`tests_viewmodel.dart` (selección alumno→cuestionario→confirmación→estado). |
| FL-04 perfil clínico | ✅ | `student_profile_screen.dart` (`_DiagnosisCard`: subtipo, severidad, riesgo, historial). Sin `FLAG_SECURE` (mismo gap que FL-01). |
| FL-05 curva de aprendizaje | ✅ | `learning_curve_viewmodel.dart` + `tracking_entity.dart` (métricas, tendencia). |
| FL-06 alertas de estancamiento | ✅ | `tracking_viewmodel.dart` (`alerts`, `unreadAlerts`, `markRead()`), bandeja + badge en `dashboard_screen.dart` con navegación al perfil. |
| FL-07 reportes PDF | ❌ | `api_client.dart` tiene `download()` genérico, pero **no hay botón de generación ni pantalla** que lo invoque, ni paquete de compartición (`share_plus`/similar) en `pubspec.yaml`. Backend (BK-10) sí genera el PDF; falta el consumo en la app. |
| FL-08 resumen del grupo | ⚠️ | `GroupMetricsEntity` (conteo por riesgo) existe y se usa parcialmente en `dashboard_viewmodel.dart`, pero no hay una pantalla dedicada de tarjetas por nivel de riesgo con ordenamiento — solo una lista de "alumnos recientes". |
| FL-09 interfaz simplificada/multisensorial | ⚠️ | Tipografía/contraste e íconos grandes vía `app_theme.dart`. **Sin apoyo auditivo**: no hay `flutter_tts` ni similar en `pubspec.yaml`. |
| FL-10 ejercicios de diagnóstico | ⚠️ | Captura y envío de respuestas funcionan (`exercise_viewmodel.dart`), con reintento de red vía interceptor Dio. El esquema reserva campos para STT (`usaStt`, `sttConfidence`) pero **no hay integración real de TTS/STT** (sin `speech_to_text`/`flutter_tts` en deps). |
| FL-11 ejercicios de intervención dinámica | ❌ | No existe feature de intervención/ajuste dinámico de dificultad en la app — solo ítems estáticos de screening. El backend sí lo soporta (`/intervention/next-exercise`, BK-08) pero la app no lo consume. |
| FL-12 retroalimentación inmediata | ❌ | Sin feedback visual (parpadeo en error) ni auditivo (TTS) al responder en `exercise_widgets.dart`. |
| FL-13 persistencia local / modo offline | ❌ | No hay cola de sincronización offline (sin `hive`/`sqflite`/`connectivity_plus` en deps); el estado del ejercicio vive solo en memoria del ViewModel durante la sesión. Sin mensaje de "sin conexión" ni protección anti-duplicados al reenviar. |
| FL-14 cliente HTTP (Dio) | ✅ | `api_client.dart`: interceptor JWT, retry en 401 con refresh token, `_mapError()` uniforme, timeouts en `api_config.dart`. |

**Gaps priorizados para cerrar HU-FL**: (1) `FLAG_SECURE` en pantallas clínicas
(FL-01/FL-04, requisito de protección de menores ligado a BD-11), (2) consumir
`/reports/{id}/generate` + descarga/compartición en la app (FL-07, el backend ya
existe), (3) integrar `flutter_tts`/`speech_to_text` para feedback multisensorial
(FL-09/FL-10/FL-12), (4) modo offline con cola local (FL-13), (5) UI de intervención
dinámica que consuma `/intervention/next-exercise` (FL-11) — actualmente solo se
aplica la batería de screening, no hay ejercicios terapéuticos adaptativos en pantalla.

## 4. Minería de Datos / PLN-ML (HU-MD) — en `Pln/` (no modificable)

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

## 5. Lo que cerró la integración PLN de esta sesión

BK-06, BK-07, BK-08, BK-12 + completitud de DB (migraciones 002 y 003). El diagnóstico
ahora usa los **modelos entrenados** (`model_version 20260618_0309`), la ruta proviene del
Recommendation Service y se persiste en `intervention.student_paths`, y los 29 ejercicios
referenciados por las 12 rutas existen en la DB.

## 6. Gaps cerrados (2026-06-23) — backend al nivel de las HU

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
