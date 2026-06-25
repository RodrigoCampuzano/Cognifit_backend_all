# Despliegue en Railway — CogniFit (guía completa y detallada)

Guía paso a paso, click por click, para dejar todo el backend corriendo en Railway
con los 3 servicios separados. Síguela de arriba a abajo.

## Arquitectura final

```
Proyecto Railway: cognifit
├─ api               público   raíz /api                  ← único con dominio
│     │ red privada (IPv6)
│     ├──► diagnosis.railway.internal:8001
│     └──► recommendation.railway.internal:8002
├─ diagnosis         privado   raíz /Pln/diagnosis_service
├─ recommendation    privado   raíz /Pln/recommendation_service
├─ Redis             plugin
└─ Postgres          Neon (externo, recomendado)  ó  plugin Railway
```

El `api` llama a los servicios PLN por la red privada
([diagnosis_client.py](../api/infrastructure/pln/diagnosis_client.py),
[recommendation_client.py](../api/infrastructure/pln/recommendation_client.py)).
Si un servicio PLN no responde, el `api` usa su pipeline local de fallback
(`PLN_FALLBACK_ENABLED=true`), así que el `api` nunca se cae por eso.

> **Por qué Railway** (comparado en jun-2026): Render gratis se duerme a los 15 min;
> Northflank gratis solo permite 2 servicios (necesitas 3); Fly/Koyeb ya no tienen
> free. Railway es el mejor PaaS para este caso (red privada nativa + monorepo
> multi-servicio), a cambio de ~$10–25/mes. La única opción 100% gratis y sin dormir
> es **Oracle VM + Neon** (ver `deploy/DEPLOY.md`).

## ⚠️ IMPORTANTE: 1 PROYECTO, VARIOS SERVICIOS (no crees proyectos por servicio)

En Railway **"Proyecto" ≠ "Servicio"**. El plan gratis limita los **proyectos**
(solo 2), pero **dentro de un proyecto puedes tener todos los servicios que quieras**.
Todo CogniFit va en **UN solo proyecto** con varios servicios dentro.

- Para crear el **primer** servicio: `New Project → Deploy from GitHub repo` (esto crea
  el proyecto y el servicio `api`).
- Para los **siguientes** (`diagnosis`, `recommendation`, `Redis`): entra al **canvas
  del mismo proyecto** y usa el botón **`+ Create`** (o `+ New` / tecla `Cmd/Ctrl+K`)
  → **GitHub Repo**. **NO** uses "New Project".

> **¿Ya creaste un proyecto aparte para `diagnosis`?** Es el error típico (por eso te
> bloqueó al ir por el 3.º). Solución: **borra ese proyecto suelto**
> (Project → Settings → Danger → Delete Project) y vuelve a añadir `diagnosis` como
> **servicio** dentro del proyecto del `api` con `+ Create → GitHub Repo`. Repite para
> `recommendation`. Así te quedas en 1 proyecto y dejas de chocar con el límite.

## Sobre el monorepo (¿se clona todo el repo?)

Un **único proyecto** con 3 servicios es la arquitectura correcta y segura (red
privada interna, los PLN **no** quedan expuestos a internet). Sobre el clonado:

- Railway clona el repo para construir, pero cada servicio usa **solo su carpeta**
  vía **Root Directory** (`/api`, `/Pln/diagnosis_service`, `/Pln/recommendation_service`).
  La imagen final de cada servicio contiene **solo esa subcarpeta**, no todo el repo.
- Con **Watch Paths** (Paso 9), un cambio en `api/**` **no** reconstruye los PLN, y
  viceversa. Cada servicio se despliega de forma aislada.
- Separar en 2 proyectos **no** reduciría el clonado (Railway clona igual) y además
  rompería la red privada, obligando a exponer los PLN públicamente. Por eso: 1
  proyecto, 3 servicios.

## Variables de entorno por servicio (plantillas)

Hay un `.example` por servicio en `deploy/env/`. En Railway las variables se pegan
en **Settings → Variables** de cada servicio.

| Servicio | Plantilla | Qué pegar en Railway |
|---|---|---|
| **api** | `deploy/env/api.env.example` | Todo el bloque (usa las URLs PLN `*.railway.internal`). |
| **diagnosis** | `deploy/env/diagnosis.env.example` | Solo `PORT=8001`. |
| **recommendation** | `deploy/env/recommendation.env.example` | Solo `PORT=8002`. |
| **Base de datos** | `deploy/env/database.env.example` | Las 2 URLs (Neon o `${{Postgres.DATABASE_URL}}`) van dentro de las variables del `api`. |

> Los servicios PLN no leen variables propias; `PORT` solo existe para que el Start
> Command enlace a `--host :: --port $PORT` en la red IPv6 de Railway.

## Configuración por servicio (referencia rápida)

Copia exactamente estos valores en cada servicio (Settings de cada uno):

| Campo | `api` | `diagnosis` | `recommendation` |
|---|---|---|---|
| Service Name | `api` | `diagnosis` | `recommendation` |
| Root Directory | `/api` | `/Pln/diagnosis_service` | `/Pln/recommendation_service` |
| Builder | Dockerfile | Dockerfile | Dockerfile |
| Start Command | `uvicorn api.main:app --host :: --port $PORT` | `uvicorn app.main:app --host :: --port $PORT` | `uvicorn app.main:app --host :: --port $PORT` |
| Healthcheck Path | `/api/v1/health` | `/health` | `/health` |
| Dominio público | **Sí** (Generate Domain) | No | No |
| Variable `PORT` | (no definir) | `8001` | `8002` |
| Watch Paths | `api/**` | `Pln/diagnosis_service/**` | `Pln/recommendation_service/**` |

Reglas de oro (las 3 causas del 90% de errores):
1. **`--host ::`** (IPv6) en los 3 start commands — la red de Railway es IPv6.
2. El **Service Name** define el host interno: `http://<nombre>.railway.internal:<PORT>`.
3. **Healthcheck Path** correcto: `/api/v1/health` solo para `api`; `/health` para los PLN.

## Checklist (marca al completar)

- [ ] 0. Prerrequisitos (cuenta, repo en GitHub, `psql` local)
- [ ] 1. Base de datos Neon creada + schema cargado
- [ ] 2. Proyecto Railway + servicio `api`
- [ ] 3. Servicio `diagnosis`
- [ ] 4. Servicio `recommendation`
- [ ] 5. Redis
- [ ] 6. Variables del `api` completas
- [ ] 7. Deploy y verificación end-to-end
- [ ] 8. Frontend + CORS
- [ ] 9. Watch Paths (mantenimiento)

---

## PASO 0 — Prerrequisitos

- Repo subido a GitHub (Railway despliega desde GitHub).
- Cuenta en https://railway.app (login con GitHub).
- `psql` y `openssl` en tu máquina:
  ```bash
  psql --version && openssl version
  # Ubuntu: sudo apt-get install -y postgresql-client openssl
  ```
- Genera ya los 2 secretos y guárdalos (los pegarás en el Paso 6):
  ```bash
  echo "JWT_SECRET_KEY=$(openssl rand -base64 48)"
  echo "DB_ENCRYPTION_KEY=$(openssl rand -base64 32)"
  ```

---

## PASO 1 — Base de datos (Neon)

> Recomendado Neon (gratis, no pausa). Si prefieres el Postgres de Railway, salta
> al recuadro al final de este paso.

1. https://neon.tech → **New Project** → región más cercana (ej. `AWS us-east-2`).
2. **Dashboard → Connect** → copia la *connection string*. Verás dos hosts:
   - **sin** `-pooler` → para migraciones (este paso).
   - **con** `-pooler` → para la app (Paso 6).
3. Carga el schema y las migraciones **en orden**, con el host **sin** `-pooler`:
   ```bash
   export PGURL="postgresql://USER:PASS@ep-xxxx.REGION.aws.neon.tech/neondb?sslmode=require"

   psql "$PGURL" -v ON_ERROR_STOP=1 -f database/schema.sql
   psql "$PGURL" -v ON_ERROR_STOP=1 -f database/002_pln_integration.sql
   psql "$PGURL" -v ON_ERROR_STOP=1 -f database/003_sync_exercises_from_bank.sql
   psql "$PGURL" -v ON_ERROR_STOP=1 -f database/004_user_roles_parent_specialist.sql
   psql "$PGURL" -v ON_ERROR_STOP=1 -f database/005_seed_test_items.sql
   ```
4. Verifica:
   ```bash
   psql "$PGURL" -c "\dn"
   # debe listar: auth, academic, assessment, diagnosis, intervention, tracking, reporting, audit
   psql "$PGURL" -c "SELECT count(*) FROM intervention.exercises;"   # > 0
   psql "$PGURL" -c "SELECT count(*) FROM assessment.test_items;"    # 120 (ítems del test)
   ```

> **Alternativa: Postgres de Railway.** En el proyecto (Paso 2) → `New → Database
> → Add PostgreSQL`. Para cargar el schema, copia la `DATABASE_PUBLIC_URL` del
> servicio Postgres (pestaña Variables) y úsala como `$PGURL` en los comandos de
> arriba. En el Paso 6 referencia `${{Postgres.DATABASE_URL}}` en vez de Neon.

---

## PASO 2 — Crear el proyecto y el servicio `api`

1. Railway → **New Project → Deploy from GitHub repo** → elige tu repo.
   Esto crea el **único proyecto** y su primer servicio (`api`). Los demás
   servicios se añaden DENTRO de este proyecto (Pasos 3-5).
2. Abre el servicio → **Settings**:
   - **Service Name**: `api`
   - **Source → Root Directory**: `/api`
   - **Build → Builder**: `Dockerfile` (se autodetecta)
   - **Deploy → Custom Start Command**:
     ```
     uvicorn api.main:app --host :: --port $PORT
     ```
     > `--host ::` (IPv6) es obligatorio: la red pública y privada de Railway es IPv6.
   - **Deploy → Healthcheck Path**: `/api/v1/health`
   - **Networking → Public Networking → Generate Domain** → te da
     `https://api-xxxx.up.railway.app`. Anótalo.
3. No despliegues aún (faltan variables). Si arranca y falla, es normal hasta el Paso 6.

---

## PASO 3 — Servicio `diagnosis` (privado)

1. **Dentro del canvas del proyecto del Paso 2**, botón **`+ Create` → GitHub Repo**
   → el **mismo** repo. (NO "New Project" — eso crearía un proyecto y chocarías con
   el límite de 2.)
2. Abre el servicio nuevo → **Settings**:
   - **Service Name**: `diagnosis`  ← el nombre define el host interno
   - **Source → Root Directory**: `/Pln/diagnosis_service`
   - **Deploy → Custom Start Command**:
     ```
     uvicorn app.main:app --host :: --port $PORT
     ```
   - **Deploy → Healthcheck Path**: `/health`
   - **Networking**: NO generes dominio público (queda solo en red privada).
3. **Variables**:
   ```
   PORT=8001
   ```
   > Fijar el puerto hace que `diagnosis.railway.internal:8001` sea estable.

---

## PASO 4 — Servicio `recommendation` (privado)

Igual que el anterior:
1. **Dentro del mismo proyecto**, botón **`+ Create` → GitHub Repo** → mismo repo.
2. **Settings**:
   - **Service Name**: `recommendation`
   - **Source → Root Directory**: `/Pln/recommendation_service`
   - **Deploy → Custom Start Command**:
     ```
     uvicorn app.main:app --host :: --port $PORT
     ```
   - **Deploy → Healthcheck Path**: `/health`
   - **Networking**: sin dominio público.
3. **Variables**:
   ```
   PORT=8002
   ```

---

## PASO 5 — Redis

1. **Dentro del mismo proyecto**, botón **`+ Create` → Database → Add Redis**.
2. No requiere configuración. Expone `${{Redis.REDIS_URL}}` (lo usarás en el Paso 6).

---

## PASO 6 — Variables del servicio `api`

Abre `api` → **Variables** → **Raw Editor** y pega esto (sustituyendo los `<...>`):

```
APP_ENV=production
PROJECT_NAME=CogniFit Escolar API
API_V1_PREFIX=/api/v1
DEBUG=false
ENABLE_SWAGGER=false
ALLOW_PUBLIC_REGISTRATION=false

# --- Base de datos (Neon, host CON -pooler) ---
DATABASE_URL=postgresql+asyncpg://USER:PASS@ep-xxxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
SYNC_DATABASE_URL=postgresql://USER:PASS@ep-xxxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
# Si usas el Postgres de Railway en vez de Neon, reemplaza las 2 líneas anteriores por:
# DATABASE_URL=${{Postgres.DATABASE_URL}}
# SYNC_DATABASE_URL=${{Postgres.DATABASE_URL}}

# --- Redis ---
REDIS_URL=${{Redis.REDIS_URL}}

# --- Servicios PLN por red privada ---
DIAGNOSIS_SERVICE_URL=http://diagnosis.railway.internal:8001
RECOMMENDATION_SERVICE_URL=http://recommendation.railway.internal:8002
PLN_TIMEOUT_SECONDS=10.0
PLN_RETRIES=1
PLN_FALLBACK_ENABLED=true

# --- Seguridad (pega los que generaste en el Paso 0) ---
JWT_SECRET_KEY=<openssl rand -base64 48>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
DB_ENCRYPTION_KEY=<openssl rand -base64 32>
PASSWORD_PEPPER=

ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=2

# --- CORS (dominio del frontend; coma-separado) ---
CORS_ORIGINS=https://tu-frontend.vercel.app

RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
LOG_LEVEL=INFO
```

> No definas `PORT` en `api`: Railway lo asigna solo al tener dominio público.

Guarda → Railway redespliega los 3 servicios.

---

## PASO 7 — Deploy y verificación end-to-end

Espera a que `api`, `diagnosis` y `recommendation` estén en estado **Active**
(verde) con healthcheck OK.

1. Salud pública del `api`:
   ```bash
   curl -fsS https://api-xxxx.up.railway.app/api/v1/health
   curl -fsS https://api-xxxx.up.railway.app/api/v1/health/db
   ```
2. Servicios internos (desde la shell del servicio `api`):
   - Dashboard → servicio `api` → botón **Connect / Shell** (o `railway ssh --service api`), y:
   ```bash
   curl -fsS http://diagnosis.railway.internal:8001/health
   curl -fsS http://recommendation.railway.internal:8002/health
   ```
3. Flujo real (a través del `api`, que internamente llama a PLN):
   `POST /api/v1/auth/login` → `POST /api/v1/screening/sessions` →
   `POST /api/v1/screening/sessions/{id}/responses` →
   `POST /api/v1/screening/sessions/{id}/diagnose`.
   La respuesta del `diagnose` debe traer `subtype`, `severity`, `risk_level` y la
   ruta recomendada.

---

## PASO 8 — Frontend y CORS

- Despliega el Flutter web en Vercel (`flutter build web --release` → subir `build/web`).
- Pon su URL final en `CORS_ORIGINS` del `api` (separa con coma si hay varias).
- En el cliente Flutter, apunta la base URL a `https://api-xxxx.up.railway.app/api/v1`.

---

## PASO 9 — Mantenimiento (Watch Paths)

Para que un push que solo toca un servicio no reconstruya los tres:

- `api` → Settings → Source → **Watch Paths**: `api/**`
- `diagnosis` → **Watch Paths**: `Pln/diagnosis_service/**`
- `recommendation` → **Watch Paths**: `Pln/recommendation_service/**`

Por servicio tienes además: logs y métricas propias, **Rollback** desde Deployments,
y ajuste de recursos (el `diagnosis` es el que más RAM consume por los modelos ML).

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `api` arranca y muere al instante | No bindeó a `$PORT`/IPv6 | Revisa el Custom Start Command: `--host :: --port $PORT` |
| Healthcheck falla en `api` | Path incorrecto | Healthcheck Path = `/api/v1/health` |
| `api` no alcanza a PLN (timeout) | Host/puerto interno mal | URL = `http://<nombre-servicio>.railway.internal:<PORT>`; el nombre debe ser exactamente `diagnosis`/`recommendation` y el `PORT` coincidir |
| `diagnosis`/`recommendation` "unhealthy" | Healthcheck Path | Debe ser `/health` (no `/api/v1/health`) |
| Error de conexión a DB / SSL | Falta SSL en Neon | Añade `?sslmode=require` a ambas URLs |
| `502` al llamar al `api` pero responde a veces | Solo bindeó IPv4 | Asegura `--host ::` (no `0.0.0.0`) |
| El diagnóstico funciona aunque PLN esté caído | Fallback local activo | Es esperado (`PLN_FALLBACK_ENABLED=true`); revisa logs de PLN si quieres el ML real |
| Migración falla a medias | Orden incorrecto | Ejecuta `schema.sql → 002 → 003 → 004` con `-v ON_ERROR_STOP=1` |

---

## Costo

Railway no es free real: $5 de prueba (30 días), luego Hobby $5/mes fijos + uso por
segundo. Con 3 servicios always-on (el `diagnosis` pesa por los modelos ML) + Redis:
**~$10–25/mes**. Para abaratar: usa **Neon** (no el Postgres de Railway) y activa los
**Watch Paths** para no reconstruir de más.
