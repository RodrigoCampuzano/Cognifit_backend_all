# CogniFit Entrega Final

Esta carpeta reemplaza los entregables anteriores. Contiene todo separado y listo para desplegar con Docker.

## Estructura

```text
cognifit_entrega_final/
├── api/                  # Backend FastAPI completo
├── database/             # Schema SQL usado por Docker y verificador DB
├── docs/                 # Plan, extracciones y analisis de integracion
├── docker-compose.yml    # Despliegue API + PostgreSQL + Redis
├── deploy.ps1            # Script Windows PowerShell
└── deploy.sh             # Script Linux/macOS/Git Bash
```

La DB de `database/schema.sql` es identica a `api/infrastructure/database/migrations/001_cognifit_schema_v2_full.sql`.
Puedes comprobarlo en `database/DB_HASHES.txt`.

## Requisitos

- Docker Desktop instalado y corriendo.
- Puerto `8000` libre para la API.
- Puerto `5432` libre para PostgreSQL.
- Puerto `6379` libre para Redis.

Si `docker` no existe en tu terminal, primero sigue:

[docs/INSTALAR_DOCKER_WINDOWS.md](docs/INSTALAR_DOCKER_WINDOWS.md)

## Despliegue en Windows

Desde PowerShell:

```powershell
cd cognifit_entrega_final
.\deploy.cmd -ResetDb
```

Si PowerShell bloquea scripts con `PSSecurityException`, usa cualquiera de estas dos opciones:

```powershell
.\deploy.cmd -ResetDb
```

o:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy.ps1 -ResetDb
```

Usa `-ResetDb` la primera vez o cuando quieras reiniciar PostgreSQL desde cero.
Si quieres conservar datos, ejecuta:

```powershell
.\deploy.cmd
```

## Despliegue en Linux/macOS/Git Bash

```bash
cd cognifit_entrega_final
chmod +x deploy.sh
./deploy.sh --reset-db
```

## URLs

- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/v1/health
- DB health: http://localhost:8000/api/v1/health/db

## Crear primer usuario admin

En desarrollo Docker esta activo `ALLOW_PUBLIC_REGISTRATION=true` para bootstrap.
Luego de crear el admin, cambia esa variable a `false` en `api/.env.docker` si quieres cerrar registros publicos.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/auth/register" `
  -ContentType "application/json" `
  -Body '{"email":"admin@cognifit.local","password":"CambiaEstaClave123!","role":"ADMIN"}'
```

Login:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"admin@cognifit.local","password":"CambiaEstaClave123!","device_info":"local"}'
```

## Verificacion manual DB

El script de despliegue ya ejecuta esta verificacion dentro del contenedor API:

```bash
docker compose exec -T api python scripts/verify_db_integration.py --database-url "postgresql://cognifit_api:cognifit_api_dev_password@postgres:5432/cognifit"
```

La verificacion revisa schemas, tablas, vistas, columnas criticas y semillas minimas:
9 modulos, 8 preguntas PRODISLEX, 28 features, codigos de error y rutas de intervencion.

## Flujo cubierto por la API

- Fase 1: PRODISLEX docente digitalizado.
- Fase 2: bateria Flutter por modulos.
- Fase 3: pipeline PLN con errores, similitud fonetica, n-gramas y vector 28D.
- Fase 4: perfil probabilistico.
- Fase 5: ruta adaptativa.
- Fase 6: seguimiento y alertas.

## Limpieza

Para apagar sin borrar datos:

```bash
docker compose down
```

Para borrar contenedores y volumenes:

```bash
docker compose down -v --remove-orphans
```
