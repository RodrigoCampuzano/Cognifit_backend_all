# Plan de Integración — Backend API ↔ Microservicios PLN

> Verificación estricta de la integración entre `api/` (FastAPI, puerto 8000) y los
> microservicios de `Pln/` **sin modificar `Pln/`**. Se permite modificar `api/` y la DB.
>
> Fecha de análisis: 2026-06-23

---

## 1. Estado actual verificado

| Componente | Puerto | Estado | Modelos |
|---|---|---|---|
| `api/` (FastAPI) | 8000 | ✅ Corre, schema DB completo | Pipeline **local** rule-based |
| `Pln/diagnosis_service` | 8001 | ✅ `/health`, `/model/info`, `/diagnose` | ✅ `.pkl` entrenados (subtype + severity) |
| `Pln/recommendation_service` | 8002 | ✅ `/health`, `/recommend`, `/next-exercise`, `/exercises/{id}`, `/routes` | Banco de ejercicios + rutas |

**Hallazgo central:** el API **no llama** a los microservicios PLN. En
[get_result.py](get_result.py) el endpoint `POST /screening/sessions/{id}/diagnose`
ejecuta un pipeline propio ([SpacyNlpService](../api/infrastructure/nlp/spacy_nlp_service.py)
\+ [RiskCalculator](../api/application/services/risk_calculator.py), rule-based "bootstrap")
y **genera la ruta localmente** desde un `ROUTES` hardcodeado. Los modelos `.pkl`
entrenados de `diagnosis_service` y el banco/adaptación de `recommendation_service`
**nunca se usan**.

- No existe cliente HTTP a 8001/8002 (`grep` de `httpx/8001/8002/diagnose` → 0 resultados de integración). `httpx==0.28.1` ya está en `requirements.txt`.
- No hay configuración de URLs de los servicios en [settings.py](../api/config/settings.py).
- El API tiene **todos los datos** para construir el request `/diagnose`
  (`expected_text`, `raw_response`, `module_code`, `response_time_ms` por respuesta —
  ver `get_session_responses` / `get_session_context`).

---

## 2. Gaps que impiden la integración (bloqueantes)

### G1 — No hay cliente hacia los microservicios PLN
El backend resuelve el diagnóstico y la ruta en memoria; ignora los modelos entrenados.

### G2 — Mismatch de enums DB ↔ contrato PLN
| Concepto | DB (`001_..._v2_full.sql`) | Devuelve el PLN | Conflicto |
|---|---|---|---|
| subtype | `PHONOLOGICAL, VISUAL_SURFACE, MIXED, NO_DYSLEXIA` | `fonologico, visual, mixto, fluidez, sin_riesgo` | **`fluidez` no tiene valor en DB**; idiomas distintos |
| severity | `MILD, MODERATE, SEVERE` | `leve, moderado, severo, ninguna` | idioma + `ninguna` |
| risk_level | `LOW, MEDIUM, HIGH` | `bajo, medio, alto` | idioma |

`pg_result_repository.save_diagnosis` castea `:subtype AS diagnosis.dyslexia_subtype`
y `:severity AS diagnosis.severity_level`: si recibe `"fonologico"`/`"fluidez"` **falla el INSERT**.

### G3 — Mapeo de módulos DB ↔ PLN
La DB usa `module_code` tipo `M05_PSEUDOWORDS`, `M02_PHONOLOGICAL_AWARENESS`.
El `/diagnose` espera `pseudopalabras`, `conciencia_fonologica`, etc. Falta tabla/mapa.

### G4 — Recommendation Service sin cablear
- Tras el diagnóstico no se llama a `/recommend` ni se persiste la ruta en
  `intervention.student_paths` (con la ruta que viene de los modelos).
- No hay endpoints API que expongan `/next-exercise` ni `/exercises/{id}` para el
  Exercise Service / Flutter.
- **Bien:** los `exercise_code` del banco (`CF_silabas_N1`, `PS_cv_N1`, …) **ya están
  sembrados** en `intervention.exercises` y en `intervention.route_templates`, así que
  los `exercise_id` que devuelve el recommendation service mapean 1:1 a la DB.

### G5 — `model_version` real no se registra
`save_diagnosis` hardcodea `'pln-rule-v1'`. El PLN devuelve su versión real
(`model_version`, p. ej. `20260618_0309`) que debe guardarse para trazabilidad (HU-BK-13).

### G6 — `error_breakdown` del PLN no se persiste como tal
El PLN devuelve `error_breakdown` y `main_error_codes` ya calculados; hoy el API los
recalcula localmente.

---

## 3. Decisión arquitectónica (recomendada)

**El API actúa como orquestador (Test Service) y delega el diagnóstico/recomendación a
los microservicios entrenados.** El pipeline local rule-based queda como **fallback**
ante `503/timeout` (el `503` significa "modelos cargando" → reintentar; si persiste,
fallback degradado marcado en `model_version`).

```
POST /screening/sessions/{id}/diagnose
   │  1. arma items desde student_responses + context
   │  2. POST 8001/diagnose ──▶ subtype/severity/risk/model_version/error_breakdown
   │  3. guarda en diagnosis.diagnoses + pipeline_runs + tracking (enum mapeado + raw PLN)
   │  4. POST 8002/recommend (subtype/severity RAW del PLN) ──▶ exercises[]
   │  5. persiste ruta en intervention.student_paths (+ route_template_id)
   ▼  devuelve diagnóstico + ruta
```

Pasar a `/recommend` los valores **RAW** del PLN (`fonologico`, `fluidez`…), no los
mapeados al enum clínico — el recommendation service solo entiende el vocabulario PLN.

---

## 4. Cambios concretos

### 4.1 Configuración — [settings.py](../api/config/settings.py)
Añadir:
```python
diagnosis_service_url: str = "http://localhost:8001"
recommendation_service_url: str = "http://localhost:8002"
pln_timeout_seconds: float = 10.0
pln_retries: int = 1            # reintento ante 503
pln_fallback_enabled: bool = True
```
Y a `.env.development` / `.env.docker` (en Docker apuntan a los nombres de servicio del compose).

### 4.2 Nuevo adapter HTTP — `infrastructure/pln/`
- `diagnosis_client.py` → `async diagnose(payload) -> dict` (httpx.AsyncClient, maneja 503→retry, 500→error, timeout→fallback).
- `recommendation_client.py` → `recommend()`, `next_exercise()`, `get_exercise()`.
- Puerto de dominio nuevo `domain/ports/diagnosis_port.py` y `recommendation_port.py` (Protocol) para mantener la arquitectura hexagonal.

### 4.3 Mapeos — un único módulo `infrastructure/pln/mappings.py`
```python
MODULE_CODE_TO_PLN = {
  "M02_PHONOLOGICAL_AWARENESS": "conciencia_fonologica",
  "M03_LETTERS_SYLLABLES":      "lectura_voz_alta",   # o el módulo PLN equivalente
  "M04_REAL_WORDS":             "palabras_reales",
  "M05_PSEUDOWORDS":            "pseudopalabras",
  "M06_SMART_DICTATION":        "dictado",
  "M07_CONTROLLED_COPY":        "copia_controlada",
  "M08_RAPID_NAMING":           "denominacion_rapida",
  "M09_READING_COMPREHENSION":  "comprension_lectora",
}
PLN_SUBTYPE_TO_ENUM = {
  "fonologico": "PHONOLOGICAL", "visual": "VISUAL_SURFACE", "mixto": "MIXED",
  "fluidez": "MIXED",            # o NO_DYSLEXIA según severidad; ver §4.4
  "sin_riesgo": "NO_DYSLEXIA",
}
PLN_SEVERITY_TO_ENUM = {"leve":"MILD","moderado":"MODERATE","severo":"SEVERE","ninguna":None}
PLN_RISK_TO_ENUM = {"bajo":"LOW","medio":"MEDIUM","alto":"HIGH"}
```
> Confirmar los `module_code` exactos contra el seed (`grep "INSERT INTO assessment.battery_modules"`).

### 4.4 DB — guardar el valor RAW del PLN (preferido sobre romper el enum)
`Pln/` no se toca, pero la DB sí. Para no perder `fluidez`/`comprension` ni el idioma:
```sql
-- migración 002_pln_integration.sql
ALTER TABLE diagnosis.diagnoses
  ADD COLUMN IF NOT EXISTS pln_subtype   TEXT,   -- 'fonologico'|'fluidez'|...
  ADD COLUMN IF NOT EXISTS pln_severity  TEXT,   -- 'leve'|'ninguna'|...
  ADD COLUMN IF NOT EXISTS model_version TEXT,   -- versión real del .pkl
  ADD COLUMN IF NOT EXISTS error_breakdown JSONB DEFAULT '{}'::jsonb;
```
La columna tipada `subtype`/`severity` se llena con el valor **mapeado**;
`pln_subtype`/`pln_severity` conservan el RAW que se reenvía a `/recommend`.
(Alternativa: `ALTER TYPE diagnosis.dyslexia_subtype ADD VALUE 'FLUENCY'/'COMPREHENSION'` —
más invasivo y rompe consumidores del enum; **no recomendado**.)

### 4.5 Use case — reescribir `GetResultUseCase.diagnose_session`
1. `context = get_session_context`; `responses = get_session_responses`.
2. Construir `items[]` (`target=expected_text`, `response=raw_response`,
   `module=MODULE_CODE_TO_PLN[module_code]`, `response_time_ms`, `input_method`).
3. `diag = await diagnosis_client.diagnose({student_id, grade, teacher_score, session_number, items})`.
4. `await recommendation_client.recommend({student_id, subtype:diag.subtype, severity:diag.severity, risk_probability, grade})`.
5. `save_diagnosis(...)` con enum mapeado + raw + `model_version` + `error_breakdown` del PLN.
6. `save_student_path(...)` → `intervention.student_paths` resolviendo `route_template_id`
   por `route_code`/`profile_code` y los `exercise_code` devueltos.
7. Fallback local solo si el cliente lanza tras agotar reintentos y `pln_fallback_enabled`.

### 4.6 Repositorio — `pg_result_repository.save_diagnosis`
- Aceptar y persistir `pln_subtype`, `pln_severity`, `model_version`, `error_breakdown` reales.
- Registrar/actualizar la fila en `diagnosis.ml_model_versions` con la `model_version` del PLN
  (en vez del fijo `pln-rule-v1`).
- Nuevo método `save_student_path(student_id, diagnosis_id, route_template_id, exercises)`.

### 4.7 Endpoints nuevos (router intervention/exercise)
- `POST /api/v1/intervention/next-exercise` → proxy validado a 8002 `/next-exercise`.
- `GET /api/v1/intervention/exercises/{exercise_id}` → 8002 `/exercises/{id}` (o desde DB).
- `GET /api/v1/health/pln` → agrega `GET 8001/health` + `8002/health` (monitoreo admin HU-BK-12).

### 4.8 Dependencias / inyección — [services.py](../api/api/dependencies/services.py)
`get_diagnosis_client()`, `get_recommendation_client()` leyendo URLs de `settings`.

---

## 5. Verificación / aceptación

1. Levantar los 3 servicios (`docker-compose` debe incluir 8001/8002 — **revisar
   [docker-compose.yml](../docker-compose.yml)**, hoy probablemente solo define el API).
2. `GET /api/v1/health/pln` → ambos `ok`.
3. Flujo e2e: teacher-results → assignments → sessions → responses → **diagnose**;
   verificar que `diagnosis.diagnoses.model_version` = versión real del `.pkl` y que
   `intervention.student_paths` tiene la ruta de 8002.
4. Caso `sin_riesgo` → ruta vacía, sin `student_paths`.
5. Caso 8001 caído → fallback local con `model_version='pln-rule-v1-fallback'`.
6. `python scripts/verify_db_integration.py` sigue en verde tras la migración 002.
7. Tests: añadir `tests/integration/test_pln/` con httpx mockeado.

---

## 6. Orden de ejecución

1. `002_pln_integration.sql` (+ correr en DB) — §4.4
2. `settings.py` + `.env*` — §4.1
3. `infrastructure/pln/` clients + mappings + ports — §4.2/4.3
4. `pg_result_repository` (persistencia raw + student_paths) — §4.6
5. `GetResultUseCase` reescrito — §4.5
6. Endpoints + dependencias — §4.7/4.8
7. `docker-compose.yml`: añadir servicios 8001/8002 — §5
8. Tests + verificación e2e — §5

### Riesgos
- **Mapeo de módulos** debe validarse contra el seed real (G3) — un código mal mapeado
  degrada el feature vector del PLN.
- El `/diagnose` agrupa **toda la batería**, pero el API diagnostica **por sesión/módulo**:
  decidir si se llama una vez por sesión (menos ítems → menor confianza, ver
  `integracion_rodrigo.md §6`) o se acumulan respuestas de todas las sesiones del
  assignment antes de diagnosticar. **Recomendado:** acumular por `assignment_id`.

---

## 7. ✅ Estado de implementación (2026-06-23)

Decisiones tomadas: **implementar todo**, **acumular por `assignment_id`**, **columnas
raw + mapeo** (enum clínico intacto). `Pln/` no se modificó.

| Cambio | Archivo |
|---|---|
| Migración 002 (pln_subtype/pln_severity/model_version/error_breakdown/pln_source en `diagnoses`; exercise_route/total_exercises/pln_profile en `student_paths`) | `api/infrastructure/database/migrations/002_pln_integration.sql` y `database/002_pln_integration.sql` |
| URLs + timeouts + fallback de servicios PLN | `api/config/settings.py`, `.env.development`, `.env.docker` |
| Puertos de dominio | `api/domain/ports/diagnosis_port.py`, `recommendation_port.py` |
| Clientes httpx (retry 503 / timeout → `PlnServiceError`) | `api/infrastructure/pln/diagnosis_client.py`, `recommendation_client.py`, `errors.py` |
| Mapeos módulos/subtipo/severidad/risk/perfil | `api/infrastructure/pln/mappings.py` |
| Orquestación 8001→8002 con fallback local | `api/application/use_cases/screening/get_result.py` |
| Persistencia raw + `model_version` real + `save_student_path` | `api/infrastructure/database/repositories/pg_result_repository.py` |
| Acumulación por assignment | `pg_session_repository.get_assignment_responses` / `complete_assignment_sessions` |
| Endpoints `/intervention/...` (active-path, next-exercise, exercises) | `api/api/v1/intervention/` |
| Inyección de clientes en `/diagnose` | `api/api/dependencies/services.py`, `api/v1/screening/router.py` |
| `GET /api/v1/health/pln` | `api/api/v1/health.py` |
| Servicios 8001/8002 + mount migración 002 | `docker-compose.yml` |
| Verificador DB ampliado | `api/scripts/verify_db_integration.py` |

**Pendiente operativo:** correr `002_pln_integration.sql` sobre la DB existente
(`docker compose up` lo aplica solo en init limpia) y validar el flujo e2e con los
3 servicios arriba. `python3 -m compileall` del paquete `api/` pasa en verde.
</content>
</invoke>
