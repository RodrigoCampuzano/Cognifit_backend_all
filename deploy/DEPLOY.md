# Despliegue GRATIS de CogniFit — Oracle Cloud + Neon (guía completa)

Guía paso a paso, de principio a fin, para dejar **todo el backend corriendo 24/7
sin costo** y sin que se apague. Síguela en orden.

- **Compute** (api + diagnosis + recommendation + redis + caddy) → **1 VM Oracle Cloud Always Free** (ARM, encendida siempre, gratis de por vida).
- **Base de datos** → **Neon** (PostgreSQL gratis que no se pausa).
- **HTTPS** → **Caddy** (certificado automático) — requiere un dominio.

## Variables de entorno por servicio (plantillas)

Hay un `.example` por servicio en `deploy/env/`. En este despliegue (Oracle/compose)
**solo el `api` necesita variables**; los servicios PLN no leen ninguna.

| Servicio | Plantilla | Variables que necesita en Oracle/compose |
|---|---|---|
| **api** | `deploy/env/api.env.example` | Todas (DB, JWT, Redis, URLs PLN, CORS). Se copia a `deploy/.env.prod` (Paso 5). |
| **diagnosis_service** | `deploy/env/diagnosis.env.example` | Ninguna (escucha en 8001 fijo). |
| **recommendation_service** | `deploy/env/recommendation.env.example` | Ninguna (escucha en 8002 fijo). |
| **Base de datos** | `deploy/env/database.env.example` | Las 2 URLs de Neon + `DB_ENCRYPTION_KEY` (van dentro del env del `api`). |

> En Oracle/compose el archivo efectivo es **`deploy/.env.prod`** (lo lee
> `docker-compose.prod.yml`). Los `deploy/env/*.example` son la referencia
> documentada de qué espera cada servicio.

## Arquitectura final

```
Neon (PostgreSQL, no pausa)  ←──SSL──┐
                                     │
[VM Oracle Cloud Always Free — Ubuntu 22.04]
   docker compose -f deploy/docker-compose.prod.yml
   ├─ caddy   :80/:443         (único expuesto a internet, HTTPS)
   ├─ api FastAPI       :8000  (interno)
   │     ├──► diagnosis_service:8001     (red interna docker)
   │     └──► recommendation_service:8002
   ├─ diagnosis_service :8001  (interno)
   ├─ recommendation_service :8002 (interno)
   └─ redis             (interno)
```

El `api` llama a los servicios PLN por la **red interna de Docker** (nombres del
compose). Si un PLN no responde, el `api` usa su pipeline local de fallback
(`PLN_FALLBACK_ENABLED=true`) y no se cae.

## Checklist

- [ ] 0. Prerrequisitos (cuenta Oracle, `psql`, `openssl`, repo en GitHub)
- [ ] 1. Base de datos Neon + schema cargado
- [ ] 2. Crear la VM Oracle Always Free
- [ ] 3. Abrir puertos (Security List **y** firewall del SO)
- [ ] 4. Instalar Docker en la VM
- [ ] 5. Clonar repo + configurar `.env.prod`
- [ ] 6. Configurar dominio/HTTPS (o modo IP)
- [ ] 7. Levantar el stack
- [ ] 8. Verificación end-to-end
- [ ] 9. Frontend + CORS
- [ ] 10. Operación y backups

---

## PASO 0 — Prerrequisitos

En tu máquina local:
```bash
psql --version && openssl version
# Ubuntu: sudo apt-get install -y postgresql-client openssl git
```
- Repo subido a GitHub (o accesible para `git clone`).
- Tarjeta de crédito para verificar la cuenta de Oracle (**Always Free no cobra**).
- Genera ya los 2 secretos y guárdalos:
  ```bash
  echo "JWT_SECRET_KEY=$(openssl rand -base64 48)"
  echo "DB_ENCRYPTION_KEY=$(openssl rand -base64 32)"
  ```

---

## PASO 1 — Base de datos (Neon)

1. https://neon.tech → **New Project** → región más cercana (ej. `AWS us-east-2`).
2. **Dashboard → Connect** → copia la *connection string*. Hay dos hosts:
   - **sin** `-pooler` → para migraciones (este paso).
   - **con** `-pooler` → para la app (Paso 5).
3. Carga schema + migraciones **en orden**, con el host **sin** `-pooler`:
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
   # auth, academic, assessment, diagnosis, intervention, tracking, reporting, audit
   psql "$PGURL" -c "SELECT count(*) FROM intervention.exercises;"   # > 0
   psql "$PGURL" -c "SELECT count(*) FROM assessment.test_items;"    # 120 (ítems del test)
   ```
   `pgcrypto`, `uuid-ossp` y `pg_trgm` ya están disponibles en Neon; el `schema.sql`
   las crea con `CREATE EXTENSION IF NOT EXISTS`. El schema **no crea roles** → 100%
   compatible con Neon sin cambios.

---

## PASO 2 — Crear la VM Oracle Always Free

1. https://www.oracle.com/cloud/free/ → crea cuenta (elige una **Home Region** con
   capacidad ARM; suelen funcionar regiones de EE. UU. o Europa).
2. Consola OCI → **Menu → Compute → Instances → Create Instance**:
   - **Name**: `cognifit`
   - **Image**: Canonical **Ubuntu 22.04**
   - **Shape**: **Change Shape → Ampere → `VM.Standard.A1.Flex`** → asigna
     **2 OCPU / 12 GB** (límite Always Free desde jun-2026; sobra para el stack).
   - **SSH keys**: **Generate a key pair** (descarga la private key) o sube tu
     `~/.ssh/id_ed25519.pub`.
   - **Create**. Anota la **IP pública** cuando la instancia quede *Running*.
3. Si sale **“Out of capacity”** en ARM: reintenta más tarde, cambia de
   *Availability Domain*, o crea la cuenta en otra Home Region. Es lo único
   realmente molesto de Oracle; es cuestión de insistir.

Conéctate:
```bash
chmod 600 ~/Descargas/ssh-key-*.key            # si descargaste la key de Oracle
ssh -i ~/Descargas/ssh-key-*.key ubuntu@IP_PUBLICA
```

---

## PASO 3 — Abrir puertos (DOS niveles, ambos obligatorios)

Oracle bloquea por defecto en **dos** capas. Hay que abrir 80 y 443 en las dos.

**A) Security List del VCN** (consola OCI):
- **Networking → Virtual Cloud Networks →** tu VCN **→ Subnet →** Default Security List
  **→ Add Ingress Rules**. Añade dos reglas:
  - Source `0.0.0.0/0`, IP Protocol TCP, Destination Port `80`
  - Source `0.0.0.0/0`, IP Protocol TCP, Destination Port `443`
  (el 22 para SSH suele venir ya abierto).

**B) Firewall del sistema operativo** (dentro de la VM, vía SSH):
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```
> Si te saltas el paso B, el sitio “no carga” aunque la Security List esté abierta.
> Es el error nº 1 con Oracle.

---

## PASO 4 — Instalar Docker en la VM

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
```
Cierra la sesión SSH y vuelve a entrar (para aplicar el grupo `docker`). Verifica:
```bash
docker --version && docker compose version
```

---

## PASO 5 — Clonar el repo y configurar variables

```bash
git clone <URL_DE_TU_REPO> cognifit && cd cognifit

cp deploy/.env.prod.example deploy/.env.prod
nano deploy/.env.prod
```

Rellena en `deploy/.env.prod`:
- `DATABASE_URL` / `SYNC_DATABASE_URL` → tu connection string de Neon con el host
  **CON** `-pooler` y `?sslmode=require`. La `DATABASE_URL` debe empezar con
  `postgresql+asyncpg://` y la `SYNC_DATABASE_URL` con `postgresql://`.
- `JWT_SECRET_KEY` y `DB_ENCRYPTION_KEY` → los que generaste en el Paso 0.
- `CORS_ORIGINS` → el dominio de tu frontend (ej. `https://tu-app.vercel.app`).

Las URLs de los PLN ya vienen correctas (red interna de Docker):
`DIAGNOSIS_SERVICE_URL=http://diagnosis_service:8001` y
`RECOMMENDATION_SERVICE_URL=http://recommendation_service:8002`.

---

## PASO 6 — Dominio y HTTPS

Edita `deploy/Caddyfile`:

- **Con dominio** (recomendado): crea un registro **A** que apunte a la IP pública
  de la VM. Si usas Cloudflare, pon el registro en modo **“DNS only”** (nube gris)
  para que Caddy pueda validar el certificado. Luego:
  ```
  api.tudominio.com {
      reverse_proxy api:8000
  }
  ```
  DNS gratis: un subdominio de **DuckDNS**, o tu dominio en **Cloudflare**.

- **Sin dominio todavía** (solo pruebas, HTTP por IP): comenta el bloque anterior y
  deja:
  ```
  :80 {
      reverse_proxy api:8000
  }
  ```

---

## PASO 7 — Levantar el stack

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
docker compose -f deploy/docker-compose.prod.yml ps      # todos "Up/healthy"
docker compose -f deploy/docker-compose.prod.yml logs -f api
```
La primera build tarda (compila dependencias del `diagnosis`). Espera a que los
healthchecks pasen a *healthy*.

---

## PASO 8 — Verificación end-to-end

```bash
# Desde la VM:
curl -fsS http://localhost:8000/api/v1/health
curl -fsS http://localhost:8000/api/v1/health/db          # debe conectar a Neon
curl -fsS http://localhost:8001/health                    # diagnosis
curl -fsS http://localhost:8002/health                    # recommendation

# Desde fuera (con dominio):
curl -fsS https://api.tudominio.com/api/v1/health
# o sin dominio:
curl -fsS http://IP_PUBLICA/api/v1/health
```
Comunicación interna api → PLN (debe responder, no timeout):
```bash
docker compose -f deploy/docker-compose.prod.yml exec api \
  python -c "import httpx,os; print(httpx.get(os.environ['DIAGNOSIS_SERVICE_URL']+'/health').json())"
```
Flujo real: `POST /api/v1/auth/login` → `/screening/sessions` →
`/screening/sessions/{id}/responses` → `/screening/sessions/{id}/diagnose`
(la respuesta trae `subtype`, `severity`, `risk_level` y la ruta recomendada).

---

## PASO 9 — Frontend y CORS

- Flutter web → `flutter build web --release` → sube `build/web` a Vercel.
- Pon la URL de Vercel en `CORS_ORIGINS` de `deploy/.env.prod` y reinicia el `api`:
  ```bash
  docker compose -f deploy/docker-compose.prod.yml up -d api
  ```
- En el cliente Flutter, base URL = `https://api.tudominio.com/api/v1`.

---

## PASO 10 — Operación y backups

```bash
# Actualizar tras un push
git pull && docker compose -f deploy/docker-compose.prod.yml up -d --build

# Reiniciar / parar / logs
docker compose -f deploy/docker-compose.prod.yml restart api
docker compose -f deploy/docker-compose.prod.yml down
docker compose -f deploy/docker-compose.prod.yml logs -f

# Backup de la DB (Neon free guarda historial limitado)
pg_dump "$PGURL" > backup_$(date +%F).sql
```
Todos los servicios tienen `restart: unless-stopped`: si la VM se reinicia, vuelven
a levantar solos. Para que arranquen tras un reboot, asegúrate de que Docker está
habilitado: `sudo systemctl enable docker`.

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| El sitio no carga desde fuera | Falta abrir puertos en el SO | Repite el Paso 3-B (iptables) y guarda con `netfilter-persistent save` |
| `curl localhost:8000/health` falla | El `api` no arrancó | `docker compose ... logs api`; revisa `DATABASE_URL` |
| Error SSL / no conecta a Neon | Falta `?sslmode=require` | Añádelo a `DATABASE_URL` y `SYNC_DATABASE_URL` |
| `health/db` falla pero `health` ok | URL async mal | `DATABASE_URL` debe empezar con `postgresql+asyncpg://` |
| Caddy no saca certificado | DNS no apunta a la VM o Cloudflare en “proxied” | Registro A → IP de la VM; Cloudflare en “DNS only” |
| “Out of capacity” al crear la VM | Sin ARM disponible en la región | Reintenta / cambia Availability Domain / otra Home Region |
| api responde aunque PLN esté caído | Fallback local activo | Esperado (`PLN_FALLBACK_ENABLED=true`); revisa logs de PLN para el ML real |
| Build muy lenta o sin memoria | RAM justa durante build | Cierra otros contenedores; la A1 con 12 GB basta |

---

## Costo y notas

- **$0 real**: la VM Oracle Always Free es 24/7 de por vida; Neon free no pausa.
- La VM es ARM (aarch64); las imágenes `python:3.12-slim` tienen build ARM, así que
  todo compila sin cambios.
- El `docker-compose.yml` de la **raíz** es solo para desarrollo local (levanta su
  propio Postgres). Este `deploy/docker-compose.prod.yml` es el de **producción**
  (DB en Neon, sin Postgres local, con Caddy).
