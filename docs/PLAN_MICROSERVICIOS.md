# Plan de Implementación — Migración a Microservicios (SOA)

> Cómo descomponer el backend actual (monolito modular FastAPI) en los microservicios
> que describen el MVP y las HU, **reaprovechando** la arquitectura hexagonal ya existente
> y los dos servicios Python que ya están separados (`Pln/diagnosis_service` 8001 y
> `Pln/recommendation_service` 8002).
>
> Fecha: 2026-06-23. Estado actual: **monolito modular** desplegado en `docker compose`.

---

## 1. Punto de partida (lo que ya tenemos a favor)

El backend NO es un monolito enmarañado: ya está organizado por **dominios** con
arquitectura limpia (puertos/adaptadores). Cada dominio tiene su router, casos de uso y
repositorios separados, y la DB usa **schemas por dominio** (`auth`, `academic`,
`assessment`, `diagnosis`, `intervention`, `tracking`, `reporting`, `audit`). Esto hace
la extracción a microservicios un *refactor de empaquetado y despliegue*, no una reescritura.

| Activo actual | Por qué ayuda a la migración |
|---|---|
| Routers por dominio (`api/v1/{auth,students,screening,intervention,tracking,reports,admin,security}`) | Cada uno mapea casi 1:1 a un microservicio |
| Capa `application/use_cases` + `domain/ports` | La lógica ya está desacoplada del transporte HTTP |
| `infrastructure/.../repositories` por agregado | Acceso a datos ya aislado por dominio |
| **Schemas PostgreSQL por dominio** | Permite "database-per-service" lógico sin reparticionar tablas |
| `diagnosis_service` (8001) y `recommendation_service` (8002) **ya separados** | 2 de 9 servicios ya existen y se consumen vía HTTP |
| JWT + RBAC + auditoría + Redis ya implementados | Base lista para el gateway y la auth distribuida |

---

## 2. Arquitectura objetivo (según MVP/HU)

```
                         ┌─────────────────────────┐
   Flutter / Web  ─────▶ │   API Gateway (HU-BK-02) │  valida JWT, rate-limit, enruta, oculta topología
                         └────────────┬────────────┘
        ┌───────────────┬─────────────┼───────────────┬────────────────┬─────────────┐
        ▼               ▼             ▼               ▼                ▼             ▼
   Auth Service   User&Groups     Test Service   Exercise Svc    Tracking&Alerts  Report Svc
   (auth schema)  (academic)      (assessment)   (intervention)  (tracking)       (reporting)
        │               │             │               │                │             │
        └───────────────┴───────────┬─┴───────────────┴────────────────┴─────────────┘
                                     ▼                         ▼
                          Diagnosis Service (8001)   Recommendation Service (8002)   ← YA EXISTEN
                          (modelos PLN/ML entrenados) (rutas adaptativas)
```

### Mapa: módulo actual → microservicio destino

| Microservicio (HU) | Puerto sug. | Sale de (código actual) | Schema(s) DB que posee |
|---|---|---|---|
| **API Gateway** (HU-BK-02) | 8080 | *nuevo* (o el API actual reducido a gateway) | — |
| **Auth Service** (HU-BK-01/03) | 8010 | `api/v1/auth`, `api/v1/admin/users`, `infrastructure/security` | `auth` |
| **User & Groups Service** (HU-BK-04) | 8011 | `api/v1/students` (+ escuelas/grupos) | `academic` |
| **Test Service** (HU-BK-05) | 8012 | `api/v1/screening` (catálogo, teacher, sessions, responses, **diagnose orquesta**) | `assessment` |
| **Diagnosis Service** (HU-BK-06) | 8001 | **ya existe** `Pln/diagnosis_service` | `diagnosis` (escribe vía Test Svc o propio) |
| **Recommendation Service** (HU-BK-07) | 8002 | **ya existe** `Pln/recommendation_service` | — (lee banco JSON) |
| **Exercise Service** (HU-BK-08) | 8013 | `api/v1/intervention` | `intervention` |
| **Tracking & Alerts Service** (HU-BK-09) | 8014 | `api/v1/tracking` | `tracking` |
| **Report Service** (HU-BK-10) | 8015 | `api/v1/reports` + ReportLab | `reporting` |
| (transversal) Auditoría/Seguridad | — | `api/v1/security`, `security/audit` | `audit` (append-only, compartido) |

> Regla de oro: **cada servicio es dueño de su(s) schema(s)**. Nadie hace `JOIN`
> cross-schema de otro servicio; se comunican por HTTP (o eventos). Hoy hay JOINs
> cross-schema (p. ej. el diagnóstico lee `academic.students`/`groups`): esos son los
> puntos a cortar (ver §5 "costuras").

---

## 3. Decisiones de arquitectura

1. **Patrón de migración: Strangler Fig.** No hay big-bang. Se extrae un servicio a la
   vez detrás del Gateway; el resto sigue en el monolito hasta ser extraído.
2. **Gateway primero.** Introducir el API Gateway apuntando 100% al monolito actual. Una
   vez que todo el tráfico pasa por él, se reenrutan paths a servicios nuevos sin que el
   cliente (Flutter) note el cambio.
3. **Base de datos: una instancia PostgreSQL, schema-per-service** (fase 1) →
   database-per-service (fase 3, opcional). Empezar con la misma DB pero **revocando
   privilegios cross-schema** por rol de DB, para forzar los límites sin migrar datos.
4. **Auth distribuida sin llamada por request:** el Gateway valida el JWT (firma + exp) y
   propaga `X-User-Id`/`X-User-Role` a los servicios internos (red privada). Los servicios
   confían en esos headers (no re-validan contra Auth en cada request). La clave pública/
   secreto JWT se comparte vía secreto de despliegue.
5. **Comunicación:** síncrona HTTP/JSON entre servicios (httpx, ya usado para 8001/8002).
   Para desacoplar efectos (p. ej. "diagnóstico creado → generar ruta → snapshot de
   tracking") introducir **eventos asíncronos** (Redis Streams ya disponible; o
   RabbitMQ/NATS) en fase 4.
6. **Reutilizar el código existente:** cada servicio nace copiando su slice vertical
   (`api/v1/<dominio>` + `application/use_cases/<dominio>` + `domain/...` + repos) a un
   nuevo proyecto FastAPI con su propio `Dockerfile` (idéntico patrón a `Pln/*`).
7. **Observabilidad:** cada servicio expone `/health` (ya hay patrón) + `/metrics`;
   el Gateway agrega el estado (como ya hace `/health/pln`).

---

## 4. Plan por fases

### Fase 0 — Preparación (1 sprint)
- Extraer un paquete compartido `cognifit_common` (auth/JWT, modelos Pydantic comunes,
  logging, errores, cliente httpx con retry). Publicarlo como lib interna o copiarlo.
- Contratos OpenAPI por dominio congelados (ya hay `/openapi.json`); versionarlos.
- Definir red Docker privada `cognifit_internal` + red pública solo para el Gateway.

### Fase 1 — API Gateway (1 sprint) · **HU-BK-02**
- Stand up del Gateway (opciones: **Traefik/Kong/APISIX** declarativo, o FastAPI+httpx si
  se quiere lógica propia). Recomendado: **Traefik** (rate-limit, TLS, routing por path).
- Mover validación JWT y rate-limiting (hoy en middlewares del monolito) al Gateway.
- Ruteo: `/(auth|students|screening|intervention|tracking|reports|admin)` → monolito.
- Resultado: cliente solo conoce el Gateway; topología oculta. Cero cambio funcional.

### Fase 2 — Extraer servicios "hoja" (2-3 sprints)
Orden por bajo acoplamiento → alto:
1. **Report Service** (HU-BK-10) — casi sin dependencias de escritura; lee diagnóstico/
   tracking por HTTP. Ideal primero.
2. **Tracking & Alerts Service** (HU-BK-09) — dueño de `tracking`; consume eventos/HTTP.
3. **Exercise Service** (HU-BK-08) — dueño de `intervention`; llama a Recommendation (8002).
4. **User & Groups Service** (HU-BK-04) — dueño de `academic`.
5. **Auth Service** (HU-BK-01/03) — dueño de `auth`; emite/valida JWT (el Gateway usa su
   JWKS/clave). Se extrae cuando el resto ya no comparte su sesión de DB.
6. **Test Service** (HU-BK-05) — el más acoplado (orquesta diagnóstico+recomendación y
   escribe en varios schemas); se extrae al final, ya apoyándose en los demás por HTTP.

Cada extracción = nuevo repo/carpeta `services/<name>/` con FastAPI + Dockerfile + su
slice de código + entrada en `docker-compose`. El Gateway reapunta ese path al nuevo
servicio y se retira del monolito.

### Fase 3 — Aislar datos (1-2 sprints)
- Crear un **rol de DB por servicio** con `GRANT` solo a su schema; `REVOKE` lo demás.
- Sustituir los JOINs cross-schema restantes por llamadas HTTP (ver §5).
- Opcional: separar en instancias/bases físicas distintas (database-per-service real).

### Fase 4 — Eventos y resiliencia (1-2 sprints)
- Introducir bus de eventos (Redis Streams / NATS) para el flujo
  `ScreeningCompleted → DiagnoseRequested → RouteAssigned → TrackingSnapshot → AlertRaised`
  (ya existen los `domain/events/*` como base).
- Patrones: outbox transaccional, reintentos idempotentes, circuit breaker en los clientes
  httpx (extender los de `infrastructure/pln`), timeouts y fallbacks (ya hay precedente con
  el fallback local del diagnóstico).

### Fase 5 — Operación (continuo)
- Orquestación: `docker compose` → **Kubernetes** (un Deployment+Service por microservicio,
  HPA por carga). Secrets/Config por servicio.
- CI/CD por servicio (build/test/deploy independiente).
- Tracing distribuido (OpenTelemetry) + logs centralizados; correlación por `X-Request-ID`
  (ya hay middleware de logging que puede propagarlo).

---

## 5. Costuras a cortar (acoplamientos actuales)

Estos son los JOINs/lecturas cross-dominio que hoy existen y deben volverse llamadas entre
servicios o duplicación controlada de datos:

| Acoplamiento actual | Servicio que lo necesita | Cómo resolver |
|---|---|---|
| `diagnose` lee `academic.students.grade`/`birth_year` y `groups.teacher_id` | Test/Diagnosis | Test Service pide el contexto del alumno a User&Groups por HTTP y lo manda al payload |
| `save_student_path` resuelve `intervention.route_templates`/`exercises` | Exercise Service | El dueño de `intervention` expone endpoint para persistir/leer la ruta |
| Reportes leen `diagnosis.v_latest_student_risk` + `intervention.student_paths` + `academic` (nombre PII) | Report Service | Report compone vía HTTP a Diagnosis/Exercise/User; descifra PII solo User&Groups |
| Tracking lee `intervention.exercise_sessions` y `diagnosis_ml_sessions` | Tracking | Exercise emite eventos de sesión; Tracking mantiene su propia serie temporal |
| RBAC por `current_setting('app.current_user_id')` (RLS) | todos | El Gateway propaga identidad; cada servicio aplica su propia autorización |
| Auditoría `audit.audit_log` escrita desde varios routers | transversal | Servicio/[librería] de auditoría con endpoint append-only o evento `AuditLogged` |

---

## 6. Riesgos y mitigaciones

- **Transacciones distribuidas:** el flujo diagnóstico→ruta hoy es una sola transacción DB.
  Al separar, usar **saga** (compensaciones) o el patrón outbox; aceptar consistencia
  eventual en tracking/reportes.
- **PII de menores cifrada (pgcrypto):** la clave de descifrado debe vivir **solo** en
  User&Groups Service; los demás reciben datos ya descifrados/seudonimizados por HTTP
  (cumple HU-BD-11 y minimiza superficie).
- **Latencia por saltos HTTP:** cachear catálogos/perfil en Redis (HU-BK-11) y usar el bus
  de eventos para lo no-crítico.
- **Sobre-fragmentación:** no extraer un servicio sin necesidad. Diagnosis/Recommendation
  ya están separados por una razón (ML pesado); el resto puede empezar como 2-3 servicios
  agrupados (p. ej. "Identity" = Auth+User&Groups) y dividirse después.

---

## 7. Primer incremento accionable (lo que yo haría ya)

1. **Gateway con Traefik** delante del monolito (Fase 1) — sin tocar lógica, todo el
   tráfico por un solo punto. Entregable verificable: `curl gateway/api/v1/health` ok.
2. **Extraer Report Service** como prueba de concepto del patrón (Fase 2.1): carpeta
   `services/report/` (FastAPI + Dockerfile + slice de `reports`), entrada en compose,
   Gateway reapunta `/reports`. Smoke test e2e adaptado.
3. Documentar el contrato HTTP que Report necesita de Diagnosis/Exercise/User → plantilla
   para las siguientes extracciones.

> Con esto se valida el patrón completo (gateway + extracción + datos por HTTP) en el
> servicio de menor riesgo, y las extracciones siguientes son repetición mecánica.
</content>
