# CogniFit — Guía de Endpoints para Diseño UI

Documento de referencia para el diseñador de interfaces: qué pantalla necesita cada
endpoint, qué campos pide el usuario (con tipo, si es obligatorio y reglas de
validación) y qué datos devuelve para mostrar.

- **Base URL**: `https://api-production-xxxx.up.railway.app/api/v1`
- **Formato**: JSON (`Content-Type: application/json`), salvo donde se indique.
- **Documentación viva (Scalar)**: `…/docs`

## Convenciones de este documento
- **Obligatorio** = el campo debe enviarse sí o sí.
- **Tipo**: `string`, `int`, `float`, `bool`, `UUID` (id), `enum` (lista cerrada), `array`.
- ⚠️ = regla de validación que la UI debe aplicar antes de enviar.

---

## 0. Autenticación (transversal a todas las pantallas)

Casi todos los endpoints exigen un **token**. Flujo en la UI:

1. Pantalla **Login** → se obtiene `access_token` (válido **15 min**) y `refresh_token`.
2. La app guarda ambos y envía en cada petición la cabecera:
   `Authorization: Bearer <access_token>`
3. Cuando una petición responda **401**, usar `refresh` para renovar sin pedir
   contraseña de nuevo. Si el refresh también falla → volver a Login.

**Roles** (definen qué ve cada usuario): `ADMIN`, `SPECIALIST`, `TEACHER`, `PARENT`, `STUDENT`.

**Errores comunes a manejar en UI:**
| Código | Significado | Qué mostrar |
|---|---|---|
| 401 | Token ausente/expirado | Renovar token o ir a Login |
| 403 | Rol sin permiso | "No tienes permisos para esta acción" |
| 404 | No encontrado | "Recurso no encontrado" |
| 409 | Conflicto (ej. email ya existe) | Mensaje específico del campo |
| 422 | Validación | Resaltar el campo inválido |

---

## 1. AUTH — Pantallas de acceso

### POST `/auth/login` — Iniciar sesión
**Auth:** no. **Pantalla:** Login.

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| email | string (email) | ✅ | campo email |
| password | string | ✅ | campo password |
| device_info | string | ❌ | opcional, ≤200 chars (ej. "Android 14 / Pixel") |

**Devuelve:** `access_token`, `refresh_token`, `expires_in_minutes`. → guardar en sesión.

### POST `/auth/refresh` — Renovar token
**Auth:** no (usa el refresh_token). **Pantalla:** ninguna (automático).

| Campo | Tipo | Obligatorio |
|---|---|---|
| refresh_token | string | ✅ |

**Devuelve:** nuevo par de tokens.

### POST `/auth/logout` — Cerrar sesión
**Auth:** sí. **Pantalla:** botón "Cerrar sesión".

| Campo | Tipo | Obligatorio |
|---|---|---|
| refresh_token | string | ✅ |

### GET `/auth/me` — Perfil del usuario actual
**Auth:** sí. **Pantalla:** encabezado/menú de usuario.
**Devuelve:** `id`, `email`, `role`, `is_active`. → para mostrar nombre/rol y decidir qué menús habilitar.

### POST `/auth/register` — Registro
**Auth:** depende. En **producción está deshabilitado** para el público; solo un
ADMIN autenticado puede crear usuarios. Para alta de usuarios usar la pantalla de
**Admin → Usuarios** (sección 3). No exponer esta pantalla a usuarios finales.

---

## 2. ESTUDIANTES

### GET `/students` — Lista de estudiantes
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** listado de alumnos.
**Devuelve:** array de estudiantes (ver campos abajo). → tabla/tarjetas.

### POST `/students` — Crear estudiante
**Auth:** ADMIN, TEACHER. **Pantalla:** formulario "Nuevo alumno".

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| group_id | UUID | ✅ | selector de grupo/grado (viene de la lista de grupos) |
| full_name | string | ✅ | ⚠️ 1–180 chars |
| birth_year | int | ❌ | ⚠️ entre **2008 y 2022** (selector de año) |
| gender | string | ❌ | ≤16 chars (ej. selector M/F/Otro) |

### GET `/students/{student_id}` — Detalle de estudiante
**Auth:** ADMIN, SPECIALIST, TEACHER, PARENT. **Pantalla:** ficha del alumno.

**Campos del estudiante (response):** `id`, `group_id`, `full_name`, `birth_year`,
`gender`, `is_active`.

---

## 3. ADMIN — Gestión de usuarios y modelos

### GET `/admin/users` — Lista de usuarios
**Auth:** ADMIN. **Pantalla:** Admin → Usuarios (tabla).

### POST `/admin/users` — Crear usuario
**Auth:** ADMIN. **Pantalla:** "Nuevo usuario".

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| email | string (email) | ✅ | campo email |
| password | string | ✅ | ⚠️ mínimo 8 chars |
| role | enum | ✅ | dropdown: ADMIN / SPECIALIST / TEACHER / PARENT / STUDENT |

### PATCH `/admin/users/{user_id}` — Editar usuario
**Auth:** ADMIN. **Pantalla:** editar usuario.

| Campo | Tipo | Obligatorio | UI |
|---|---|---|---|
| role | enum | ❌ | dropdown de roles |
| is_active | bool | ❌ | switch activar/desactivar |

### DELETE `/admin/users/{user_id}` — Eliminar usuario
**Auth:** ADMIN. **UI:** botón con confirmación.

### GET `/admin/model-versions` — Versiones del modelo ML
**Auth:** ADMIN, SPECIALIST. **Pantalla:** Admin → Modelos (lista de versiones).

### POST `/admin/model-versions/activate` — Activar versión de modelo
**Auth:** ADMIN.

| Campo | Tipo | Obligatorio | UI |
|---|---|---|---|
| version_tag | string | ✅ | selector de versión disponible |

---

## 4. SCREENING — Cuestionario docente + batería de test

> Este es el flujo central. Orden de pantallas:
> **(1) Cuestionario docente → (2) Asignar batería → (3) Sesión por módulo →
> (4) Capturar respuestas → (5) Diagnóstico → (6) Ver riesgo.**

### GET `/screening/teacher-items` — Preguntas del cuestionario docente
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** cuestionario docente (carga las 8 preguntas).
**Devuelve:** lista de ítems (texto de cada pregunta + su `item_code`). → renderizar las preguntas.

### POST `/screening/teacher-results` — Enviar cuestionario docente
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** cuestionario docente (envío).

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| student_id | UUID | ✅ | alumno seleccionado |
| answers | array | ✅ | ⚠️ **exactamente 8** respuestas |
| answers[].item_code | string | ✅ | viene de `teacher-items` |
| answers[].value | enum (texto o número) | ✅ | **Nunca=0**, **A veces=0.5**, **Frecuente=1** (3 botones por pregunta) |

**Devuelve:** `score` (0–100), `battery_mode`, `enabled_module_codes` (qué módulos
activar después), `risk_flags`. → mostrar resultado y pasar a asignación.

### GET `/screening/catalog` — Catálogo de la batería
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** selección de módulos / vista de batería.
**Devuelve:** módulos disponibles (código, nombre, si usan TTS/STT). → construir la batería visual.

### GET `/screening/item-bank/tede` — Banco de ítems TEDE
**Auth:** ADMIN, SPECIALIST, TEACHER. **Uso:** consulta del banco de ítems (admin/diseño de test).

### POST `/screening/assignments` — Asignar batería al alumno
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** "Asignar test".

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| student_id | UUID | ✅ | alumno |
| teacher_score | float | ✅ | ⚠️ 0–100 (viene del cuestionario docente) |
| risk_flags | array | ❌ | opcional (viene del cuestionario) |

**Devuelve:** `enabled_module_codes` + `assignments` (con sus IDs). → cada assignment abre una sesión.

### POST `/screening/sessions` — Abrir sesión de un módulo
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT. **Pantalla:** inicio de cada módulo del test.

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| assignment_id | UUID | ✅ | viene de assignments |
| module_code | string | ✅ | ⚠️ 3–64 chars (módulo a iniciar) |
| device_id | string | ❌ | ≤120 chars |
| app_version | string | ❌ | ≤40 chars |
| raw_client_payload | objeto | ❌ | metadata libre del cliente |

**Devuelve:** la sesión con su `session_id`. → usar para pedir los ítems y enviar respuestas.

### GET `/screening/sessions/{session_id}/items` — Ítems a mostrar en la app
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT. **Pantalla:** el test en curso (renderiza cada ítem).
**Devuelve:** la lista de ítems del módulo de la sesión, cada uno con su `item_id`
(necesario para enviar la respuesta), `stimulus_text` (lo que se muestra/lee),
`item_kind`, `difficulty`, `item_order` y `module_code`. → la UI pinta los ítems en
orden y guarda el `item_id` de cada uno para el envío.

> Este es el endpoint que faltaba para que el alumno pueda **ver y responder** el test.
> Flujo: abrir sesión → **pedir ítems aquí** → mostrar → enviar respuestas.

### POST `/screening/sessions/{session_id}/responses` — Enviar respuestas del test
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT. **Pantalla:** durante el test (cada ítem).

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| responses | array | ✅ | ⚠️ 1–200 ítems |
| responses[].item_id | UUID | ✅ | ítem que se respondió |
| responses[].raw_response | string | ❌ | lo que produjo el alumno (≤2000); vacío si no respondió |
| responses[].response_time_ms | int | ❌ | ⚠️ 0–300000 (tiempo de respuesta) |
| responses[].capture_modality | string | ❌ | ej. `stt` / `teclado` / `tactil` (≤40) |
| responses[].response_audio_url | string | ❌ | URL del audio si hubo grabación (≤2000) |
| responses[].stt_confidence | float | ❌ | ⚠️ 0–1 (confianza del reconocimiento de voz) |

### POST `/screening/sessions/{session_id}/diagnose` — Generar diagnóstico
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** "Finalizar y diagnosticar".
**Sin body** (solo el `session_id` en la URL). Aquí el backend llama al motor PLN/ML.

**Devuelve (mostrar en pantalla de resultado).** Ojo: trae **dos vocabularios** —
el clínico (enum, en inglés) y el del PLN (en español, más amigable para mostrar):

| Campo | Valores | UI |
|---|---|---|
| subtype | `PHONOLOGICAL` / `VISUAL_SURFACE` / `MIXED` / `NO_DYSLEXIA` (enum clínico) | uso interno |
| **pln_subtype** | `fonologico` / `visual` / `mixto` / `fluidez` / `sin_riesgo` | **etiqueta a mostrar** |
| severity | `MILD` / `MODERATE` / `SEVERE` / `null` (enum) | uso interno |
| **pln_severity** | `leve` / `moderado` / `severo` / `ninguna` | **badge a mostrar** |
| risk_probability | 0.0–1.0 | barra/porcentaje |
| risk_level | `LOW` / `MEDIUM` / `HIGH` | semáforo (verde/ámbar/rojo) |
| main_error_codes | lista de errores predominantes (OMI, INV, …) | chips |
| recommended_route | exercise_ids sugeridos | enlace a la ruta |
| recommendation_reason | texto explicativo | subtítulo |

> Para mostrar al usuario usa **`pln_subtype`/`pln_severity`** (español). El `subtype`/
> `severity` en inglés son los valores clínicos internos. `risk_level` siempre es
> `LOW/MEDIUM/HIGH` (equivalen a bajo/medio/alto).

### GET `/screening/students/{student_id}/latest-risk` — Último riesgo del alumno
**Auth:** ADMIN, SPECIALIST, TEACHER, PARENT. **Pantalla:** ficha del alumno / dashboard.
**Devuelve:** el diagnóstico más reciente (mismos campos que arriba). → tarjeta de estado.

---

## 5. INTERVENCIÓN — Ruta de ejercicios

### GET `/intervention/students/{student_id}/active-path` — Ruta activa del alumno
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT, PARENT. **Pantalla:** "Mi ruta" / plan del alumno.
**Devuelve:** la ruta con sus ejercicios ordenados. → lista de ejercicios con progreso.

### POST `/intervention/students/{student_id}/next-exercise` — Siguiente ejercicio
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT. **Pantalla:** al terminar un ejercicio.

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| current_route | array de string | ✅ | exercise_ids de la ruta, en orden |
| session_history | array | ❌ | historial reciente |
| session_history[].exercise_id | string | ✅ (si se envía) | id del ejercicio |
| session_history[].accuracy | float | ✅ (si se envía) | ⚠️ 0–1 (precisión lograda) |

**Devuelve:** `exercise_id` siguiente + `action` (`start` / `continue` / `level_up` /
`add_support` / `route_completed` / `route_empty`) + `exercise_detail`. → decide qué
ejercicio mostrar y si activar apoyo TTS.

### GET `/intervention/exercises/{exercise_id}` — Detalle de un ejercicio
**Auth:** ADMIN, SPECIALIST, TEACHER, STUDENT. **Pantalla:** ejercicio en curso.
**Devuelve:** contenido completo del ejercicio (título, instrucción, ítems, `usa_tts`,
`usa_stt`, nivel, etc.). → renderizar la actividad.

---

## 6. TRACKING — Progreso y alertas

### GET `/tracking/students/{student_id}/learning-curve` — Curva de aprendizaje
**Auth:** ADMIN, SPECIALIST, TEACHER, PARENT. **Pantalla:** gráfico de evolución del alumno.

### GET `/tracking/students/{student_id}/metrics` — Métricas del alumno
**Auth:** ADMIN, SPECIALIST, TEACHER, PARENT. **Pantalla:** KPIs del alumno.

### GET `/tracking/groups/{group_id}/metrics` — Métricas del grupo
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** dashboard del grupo/clase.

### GET `/tracking/alerts` — Alertas
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** bandeja de alertas/notificaciones.
**Devuelve:** lista de alertas (con urgencia/acción sugerida). → badge de notificaciones.

### POST `/tracking/alerts/{alert_id}/read` — Marcar alerta como leída
**Auth:** ADMIN, SPECIALIST, TEACHER. **UI:** acción sobre cada alerta. Sin body.

### POST `/tracking/students/{student_id}/evaluate-progress` — Evaluar progreso
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** botón "Evaluar progreso". Sin body obligatorio.

---

## 7. REPORTES

### POST `/reports` — Solicitar reporte
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** "Generar reporte".

| Campo | Tipo | Obligatorio | Reglas / UI |
|---|---|---|---|
| student_id | UUID | ✅ | alumno |
| report_type | enum | ✅ | dropdown: **PARENT_SUMMARY** (resumen familias) / **SPECIALIST_FULL** (completo) / **GROUP_OVERVIEW** (grupo) |

**Devuelve:** el reporte solicitado con su `id` (estado en proceso, 202). → guardar id.

### GET `/reports/students/{student_id}/payload` — Datos del reporte
**Auth:** ADMIN, SPECIALIST, TEACHER. **Pantalla:** vista previa del reporte (datos crudos).

### POST `/reports/{report_id}/generate` — Generar el PDF
**Auth:** ADMIN, SPECIALIST, TEACHER. **UI:** botón "Generar PDF". Sin body.

### GET `/reports/{report_id}/download` — Descargar el PDF
**Auth:** ADMIN, SPECIALIST, TEACHER. **UI:** botón "Descargar". Devuelve un archivo (PDF), no JSON.

---

## 8. SEGURIDAD (paneles de administración)

### GET `/security/controls` — Controles de seguridad
**Auth:** ADMIN, SPECIALIST. **Pantalla:** panel de seguridad (solo lectura).

### POST `/security/audit` — Registrar evento de auditoría
**Auth:** ADMIN, SPECIALIST.

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| action | string | ✅ | ⚠️ 3–120 chars |
| target_table | string | ❌ | ≤120 |
| target_id | string | ❌ | — |
| metadata | objeto | ❌ | datos extra |

### POST `/security/remote-wipe` — Borrado remoto de dispositivo
**Auth:** ADMIN. **UI:** acción crítica, con confirmación.

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| user_id | string | ✅ | usuario objetivo |
| device_id | string | ❌ | dispositivo específico |
| reason | string | ✅ | ⚠️ 3–200 chars (motivo) |

---

## 9. HEALTH (no UI; monitoreo)

| Endpoint | Auth | Devuelve |
|---|---|---|
| GET `/health` | no | estado del API |
| GET `/health/db` | no | conexión a la base de datos |
| GET `/health/pln` | no | estado de los servicios PLN (diagnosis/recommendation) |

Útiles para una pantalla interna de "Estado del sistema" (solo ADMIN), no para el usuario final.

---

## 10. Catálogos / valores fijos (para dropdowns y badges)

| Concepto | Valores |
|---|---|
| **Roles** | ADMIN, SPECIALIST, TEACHER, PARENT, STUDENT |
| **Respuesta cuestionario docente** | Nunca (0), A veces (0.5), Frecuente (1) |
| **Subtipo (mostrar, `pln_subtype`)** | fonologico, visual, mixto, fluidez, sin_riesgo |
| **Subtipo (enum interno, `subtype`)** | PHONOLOGICAL, VISUAL_SURFACE, MIXED, NO_DYSLEXIA |
| **Severidad (mostrar, `pln_severity`)** | leve, moderado, severo, ninguna |
| **Severidad (enum interno, `severity`)** | MILD, MODERATE, SEVERE, null |
| **Nivel de riesgo (`risk_level`)** | LOW, MEDIUM, HIGH (= bajo/medio/alto) |
| **Modalidad de captura** | stt, teclado, tactil |
| **Acción de siguiente ejercicio** | start, continue, level_up, add_support, route_completed, route_empty |
| **Tipo de reporte** | PARENT_SUMMARY, SPECIALIST_FULL, GROUP_OVERVIEW |
| **Año de nacimiento (alumno)** | 2008–2022 |
| **Contraseña** | registro admin: ≥8; registro/login general: ≥12 |

---

## Notas de validación para la UI
- Las contraseñas del flujo público/`auth` exigen **≥12 caracteres**; las creadas
  desde **Admin → Usuarios** exigen **≥8**. Aplicar el mínimo correcto según pantalla.
- El cuestionario docente debe enviar **exactamente 8 respuestas** (ni más ni menos).
- `teacher_score` y cualquier porcentaje van en **0–100**; las `accuracy`/`confidence`
  van en **0.0–1.0**.
- Todos los `id` son **UUID** (string). La UI debe tratarlos como opacos (no editar a mano).
- El `access_token` dura **15 min**: implementar refresh automático ante 401.
