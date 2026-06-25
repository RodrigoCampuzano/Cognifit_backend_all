# CogniFit — Ejemplos JSON por Endpoint (para mockups UI)

Ejemplos reales de **request** y **response** de cada endpoint, para que el diseñador
use datos concretos en las interfaces sin tener que preguntar. Acompaña a
`API_UI_GUIA.md` (que explica campos, tipos y validaciones).

- Todas las peticiones (salvo login/refresh) llevan la cabecera:
  `Authorization: Bearer <access_token>`
- Los `id` son UUID de ejemplo; en runtime serán otros.
- Donde se indica *(representativo)*, la forma exacta puede variar según los datos.

---

## 1. AUTH

### POST `/auth/login`
**Request**
```json
{ "email": "admin@cognifit.com", "password": "AdminCognifit2026", "device_info": "Android 14 / Pixel 7" }
```
**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_minutes": 15
}
```

### POST `/auth/refresh`
**Request**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```
**Response 200** — mismo formato que login (nuevo par de tokens).

### POST `/auth/logout`
**Request**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```
**Response 204** — sin cuerpo.

### GET `/auth/me`
**Response 200**
```json
{ "id": "b3f1c2a4-1111-2222-3333-444455556666", "email": "admin@cognifit.com", "role": "ADMIN", "is_active": true }
```

---

## 2. ESTUDIANTES

### GET `/students`
**Response 200**
```json
[
  {
    "id": "11111111-aaaa-bbbb-cccc-222222222222",
    "group_id": "99999999-0000-1111-2222-333333333333",
    "full_name": "María Pérez López",
    "birth_year": 2017,
    "gender": "F",
    "is_active": true
  }
]
```

### POST `/students`
**Request**
```json
{ "group_id": "99999999-0000-1111-2222-333333333333", "full_name": "María Pérez López", "birth_year": 2017, "gender": "F" }
```
**Response 201**
```json
{
  "id": "11111111-aaaa-bbbb-cccc-222222222222",
  "group_id": "99999999-0000-1111-2222-333333333333",
  "full_name": "María Pérez López",
  "birth_year": 2017,
  "gender": "F",
  "is_active": true
}
```

### GET `/students/{student_id}`
**Response 200** — mismo objeto que arriba.

---

## 3. ADMIN

### GET `/admin/users` (filtros opcionales `?role=TEACHER&include_inactive=false`)
**Response 200**
```json
[
  { "id": "b3f1c2a4-1111-2222-3333-444455556666", "email": "admin@cognifit.com", "role": "ADMIN", "is_active": true, "created_at": "2026-06-25T14:30:00Z" },
  { "id": "c4a2d3b5-2222-3333-4444-555566667777", "email": "docente1@colegio.edu", "role": "TEACHER", "is_active": true, "created_at": "2026-06-25T15:00:00Z" }
]
```

### POST `/admin/users`
**Request**
```json
{ "email": "docente1@colegio.edu", "password": "Docente2026", "role": "TEACHER" }
```
**Response 201**
```json
{ "id": "c4a2d3b5-2222-3333-4444-555566667777", "email": "docente1@colegio.edu", "role": "TEACHER", "is_active": true, "created_at": "2026-06-25T15:00:00Z" }
```

### PATCH `/admin/users/{user_id}`
**Request**
```json
{ "role": "SPECIALIST", "is_active": true }
```
**Response 200**
```json
{ "id": "c4a2d3b5-2222-3333-4444-555566667777", "email": "docente1@colegio.edu", "role": "SPECIALIST", "is_active": true }
```

### DELETE `/admin/users/{user_id}` (baja lógica)
**Response 200**
```json
{ "id": "c4a2d3b5-2222-3333-4444-555566667777", "email": "docente1@colegio.edu", "role": "SPECIALIST", "is_active": false }
```

### GET `/admin/model-versions`
**Response 200** *(representativo)*
```json
[
  { "id": "m1", "version_tag": "pln-rule-v1", "algorithm": "RuleBased+NLPFallback", "is_production": true, "f1_score": 0.85, "train_date": "2026-06-25" }
]
```

### POST `/admin/model-versions/activate`
**Request**
```json
{ "version_tag": "20260618_0309" }
```
**Response 200** *(representativo)*
```json
{ "id": "m2", "version_tag": "20260618_0309", "is_production": true }
```
**Error 422** si el modelo no cumple métricas mínimas.

---

## 4. SCREENING

### GET `/screening/teacher-items`
**Response 200**
```json
[
  { "item_code": "P01", "prompt": "Confunde letras de forma o sonido parecido (b/d, p/q, m/n).", "weight": 1.0, "tags": ["visual"], "source_note": "PRODISLEX", "scale": { "Nunca": 0, "A veces": 0.5, "Frecuente": 1 } }
]
```

### POST `/screening/teacher-results`
**Request** (exactamente 8 respuestas)
```json
{
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "answers": [
    { "item_code": "P01", "value": 1 },
    { "item_code": "P02", "value": 0.5 },
    { "item_code": "P03", "value": 0 },
    { "item_code": "P04", "value": 1 },
    { "item_code": "P05", "value": 0.5 },
    { "item_code": "P06", "value": 0 },
    { "item_code": "P07", "value": 1 },
    { "item_code": "P08", "value": 0.5 }
  ]
}
```
**Response 201**
```json
{
  "id": "55555555-aaaa-bbbb-cccc-666666666666",
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "teacher_id": "c4a2d3b5-2222-3333-4444-555566667777",
  "score": 62.5,
  "battery_mode": "FULL",
  "answers": [ { "item_code": "P01", "value": 1 } ],
  "risk_flags": [ { "flag": "visual", "level": "medium" } ],
  "enabled_module_codes": ["M02_PHONOLOGICAL_AWARENESS", "M04_REAL_WORDS", "M05_PSEUDOWORDS"]
}
```

### GET `/screening/catalog`
**Response 200** *(representativo)*
```json
[
  { "module_number": 2, "module_code": "M02_PHONOLOGICAL_AWARENESS", "name": "Conciencia fonológica", "usa_tts": true, "usa_stt": true },
  { "module_number": 5, "module_code": "M05_PSEUDOWORDS", "name": "Pseudopalabras", "usa_tts": true, "usa_stt": true }
]
```

### POST `/screening/assignments`
**Request**
```json
{ "student_id": "11111111-aaaa-bbbb-cccc-222222222222", "teacher_score": 62.5, "risk_flags": [] }
```
**Response 201**
```json
{
  "enabled_module_codes": ["M02_PHONOLOGICAL_AWARENESS", "M05_PSEUDOWORDS"],
  "assignments": [
    { "id": "77777777-aaaa-bbbb-cccc-888888888888", "student_id": "11111111-aaaa-bbbb-cccc-222222222222", "test_id": "aaaa1111-...", "status": "PENDING", "assigned_at": "2026-06-25T16:00:00Z", "module_code": "M05_PSEUDOWORDS" }
  ]
}
```

### POST `/screening/sessions`
**Request**
```json
{ "assignment_id": "77777777-aaaa-bbbb-cccc-888888888888", "module_code": "M05_PSEUDOWORDS", "device_id": "tablet-aula-03", "app_version": "1.0.0", "raw_client_payload": {} }
```
**Response 201**
```json
{ "id": "ssssssss-aaaa-bbbb-cccc-999999999999", "assignment_id": "77777777-aaaa-bbbb-cccc-888888888888", "module_id": "mod-05-id", "session_status": "IN_PROGRESS", "started_at": "2026-06-25T16:05:00Z", "device_id": "tablet-aula-03", "app_version": "1.0.0" }
```

### POST `/screening/sessions/{session_id}/responses`
**Request**
```json
{
  "responses": [
    { "item_id": "item-1111-...", "raw_response": "pime", "response_time_ms": 6500, "capture_modality": "stt", "stt_confidence": 0.82 },
    { "item_id": "item-2222-...", "raw_response": "casa", "response_time_ms": 2100, "capture_modality": "stt", "stt_confidence": 0.95 }
  ]
}
```
**Response 201**
```json
{
  "session_id": "ssssssss-aaaa-bbbb-cccc-999999999999",
  "responses": [
    { "id": "resp-1", "item_id": "item-1111-...", "raw_response": "pime", "normalized_response": "pime", "is_correct": false, "error_tags": ["OMI"], "edit_distance": 1, "phonetic_similarity": 0.8, "ngram_overlap": 0.6, "lexicalization_flag": false, "error_breakdown": { "OMI": 1 } }
  ]
}
```

### POST `/screening/sessions/{session_id}/diagnose`
**Request:** *(sin cuerpo)*
**Response 200**
```json
{
  "id": "diag-aaaa-bbbb-cccc-dddd",
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "assignment_id": "77777777-aaaa-bbbb-cccc-888888888888",
  "subtype": "PHONOLOGICAL",
  "severity": "MILD",
  "risk_probability": 0.994,
  "risk_level": "HIGH",
  "main_error_codes": ["OMI", "INV"],
  "pln_subtype": "fonologico",
  "pln_severity": "leve",
  "model_version": "20260618_0309",
  "pln_source": "service",
  "diagnosed_at": "2026-06-25T16:20:00Z",
  "recommended_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
  "recommendation_reason": "Falla más en pseudopalabras que en palabras reales; patrón fonológico.",
  "feature_vector_28": [0.4, 0.0, 0.2, "..."]
}
```
> Para mostrar: usa `pln_subtype` ("fonologico") y `pln_severity` ("leve"). `risk_level`
> = `HIGH` → semáforo rojo. Si `pln_source` = `"fallback"`, el ML real no respondió y
> se usó el pipeline local.

### GET `/screening/students/{student_id}/latest-risk`
**Response 200** *(representativo; refleja el último diagnóstico)*
```json
{
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "subtype": "PHONOLOGICAL",
  "pln_subtype": "fonologico",
  "severity": "MILD",
  "risk_level": "HIGH",
  "risk_probability": 0.994,
  "diagnosed_at": "2026-06-25T16:20:00Z"
}
```

---

## 5. INTERVENCIÓN

### GET `/intervention/students/{student_id}/active-path`
**Response 200**
```json
{
  "id": "path-aaaa-bbbb",
  "exercise_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
  "total_exercises": 3,
  "pln_profile": "fonologico",
  "current_difficulty": 1,
  "route_reason": "Ruta adaptativa generada: 3 ejercicios para perfil fonologico/leve.",
  "assigned_at": "2026-06-25T16:21:00Z",
  "route_code": "RT_FONO_LEVE"
}
```
**404** si el alumno no tiene ruta activa.

### POST `/intervention/students/{student_id}/next-exercise`
**Request**
```json
{
  "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
  "session_history": [
    { "exercise_id": "CF_silabas_N1", "accuracy": 0.95 },
    { "exercise_id": "CF_silabas_N1", "accuracy": 0.92 },
    { "exercise_id": "CF_silabas_N1", "accuracy": 0.91 }
  ]
}
```
**Response 200**
```json
{
  "student_id": 21,
  "exercise_id": "CF_fonema_inicial_N1",
  "action": "level_up",
  "trigger": "accuracy 93% en 3 sesiones",
  "support": null,
  "exercise_detail": { "exercise_id": "CF_fonema_inicial_N1", "tipo": "conciencia_fonologica", "titulo": "¿Con qué sonido empieza?", "usa_tts": true, "usa_stt": true, "nivel": 1 }
}
```

### GET `/intervention/exercises/{exercise_id}`
**Response 200**
```json
{
  "exercise_id": "CF_silabas_N1",
  "tipo": "conciencia_fonologica",
  "subtipo": "segmentacion_silabica",
  "perfil_objetivo": ["fonologico", "mixto"],
  "nivel": 1,
  "grados": ["1", "2"],
  "titulo": "¿Cuántas sílabas tiene?",
  "instruccion": "Escucha la palabra y toca cuántas sílabas tiene.",
  "modalidad": "tactil_tts",
  "usa_tts": true,
  "usa_stt": false,
  "items": [
    { "palabra": "sol", "silabas": 1 },
    { "palabra": "casa", "silabas": 2 },
    { "palabra": "mariposa", "silabas": 4 }
  ]
}
```

---

## 6. TRACKING

### GET `/tracking/students/{student_id}/learning-curve`
**Response 200**
```json
{
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "diagnostic_sessions": [
    { "session_number": 1, "session_date": "2026-06-25", "accuracy": 0.62, "error_rate": 0.38, "avg_response_ms": 5200, "risk_probability": 0.99, "risk_level": "HIGH", "subtype": "fonologico", "severity": "leve" }
  ],
  "exercise_sessions": [
    { "started_at": "2026-06-26T09:00:00Z", "completed_at": "2026-06-26T09:08:00Z", "score": 80, "accuracy_pct": 0.80, "avg_response_ms": 3100, "exercise_code": "CF_silabas_N1", "title": "¿Cuántas sílabas tiene?" }
  ]
}
```

### GET `/tracking/students/{student_id}/metrics`
**Response 200**
```json
{
  "diagnostic_sessions": 2,
  "exercise_sessions": 7,
  "latest_risk_level": "MEDIUM",
  "latest_subtype": "fonologico",
  "latest_severity": "leve",
  "recent_avg_accuracy": 0.86,
  "first_accuracy": 0.70,
  "last_accuracy": 0.91,
  "trend": "improving"
}
```
> `trend`: `improving` / `regressing` / `flat` / `n/a` → flecha de tendencia.

### GET `/tracking/groups/{group_id}/metrics`
**Response 200**
```json
{ "group_id": "99999999-0000-1111-2222-333333333333", "total_students": 28, "high_risk": 4, "medium_risk": 7, "low_risk": 17 }
```

### GET `/tracking/alerts` (opcional `?only_unread=true`)
**Response 200**
```json
[
  {
    "id": "alert-aaaa",
    "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
    "alert_type": "STAGNATION",
    "message": "Estancamiento: sin mejora en las últimas 5 sesiones.",
    "suggested_action": "Revisar la ruta y considerar apoyo adicional (TTS/segmentación).",
    "urgency": "HIGH",
    "is_read": false,
    "created_at": "2026-06-26T10:00:00Z",
    "read_at": null,
    "source_session_id": null
  }
]
```
> `urgency`: `HIGH` / `MEDIUM` / `LOW`. `alert_type`: `STAGNATION` / `LEVEL_UP`.

### POST `/tracking/alerts/{alert_id}/read`
**Response 200**
```json
{ "id": "alert-aaaa", "is_read": true, "read_at": "2026-06-26T10:05:00Z" }
```

### POST `/tracking/students/{student_id}/evaluate-progress` (opcional `?window=5`)
**Response 200**
```json
{
  "student_id": "11111111-aaaa-bbbb-cccc-222222222222",
  "evaluated": true,
  "sessions_considered": 5,
  "action": "level_up",
  "alert": { "id": "alert-bbbb", "alert_type": "LEVEL_UP", "urgency": "MEDIUM", "message": "Recalibración sugerida: >90% de aciertos en las últimas 3 sesiones.", "created_at": "2026-06-26T10:10:00Z" }
}
```
> `action`: `none` / `level_up` / `stagnation`. `alert` puede ser `null`.

---

## 7. REPORTES

### POST `/reports`
**Request**
```json
{ "student_id": "11111111-aaaa-bbbb-cccc-222222222222", "report_type": "PARENT_SUMMARY" }
```
**Response 202** *(representativo)*
```json
{ "id": "rep-aaaa", "student_id": "11111111-aaaa-bbbb-cccc-222222222222", "report_type": "PARENT_SUMMARY", "status": "PENDING" }
```

### GET `/reports/students/{student_id}/payload`
**Response 200** *(representativo: datos que compondrán el reporte)*
```json
{
  "student": { "full_name": "María Pérez López", "birth_year": 2017 },
  "latest_diagnosis": { "pln_subtype": "fonologico", "pln_severity": "leve", "risk_level": "HIGH" },
  "route": { "total_exercises": 3, "exercise_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"] }
}
```

### POST `/reports/{report_id}/generate`
**Response 200** *(representativo)*
```json
{ "id": "rep-aaaa", "status": "GENERATED", "file_ready": true }
```

### GET `/reports/{report_id}/download`
**Response 200** — devuelve el **archivo PDF** (`Content-Type: application/pdf`), no JSON.

---

## 8. SEGURIDAD

### GET `/security/controls`
**Response 200** *(representativo)*
```json
{ "rbac": true, "rls": true, "rate_limit": true, "pii_encryption": true, "audit_log": true }
```

### POST `/security/audit`
**Request**
```json
{ "action": "EXPORT_REPORT", "target_table": "reporting.report_requests", "target_id": "rep-aaaa", "metadata": { "format": "pdf" } }
```
**Response 201** *(representativo)*
```json
{ "id": "audit-aaaa", "action": "EXPORT_REPORT", "logged_at": "2026-06-26T11:00:00Z" }
```

### POST `/security/remote-wipe`
**Request**
```json
{ "user_id": "c4a2d3b5-2222-3333-4444-555566667777", "device_id": "tablet-aula-03", "reason": "Dispositivo extraviado" }
```
**Response 202** *(representativo)*
```json
{ "status": "WIPE_REQUESTED", "user_id": "c4a2d3b5-2222-3333-4444-555566667777", "device_id": "tablet-aula-03" }
```

---

## 9. HEALTH

### GET `/health`
```json
{ "status": "ok" }
```
### GET `/health/db`
```json
{ "status": "ok", "db": 1 }
```
### GET `/health/pln`
```json
{
  "status": "ok",
  "diagnosis": { "status": "up", "service": "diagnosis" },
  "recommendation": { "status": "up", "service": "recommendation" }
}
```
(si falla: `status: "degraded"` y cada servicio en `"down"` con su `error`.)
