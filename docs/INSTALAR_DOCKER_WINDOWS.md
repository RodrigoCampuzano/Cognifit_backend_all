# Instalar Docker Desktop en Windows

Tu error:

```text
docker : El termino 'docker' no se reconoce...
```

significa que Windows no tiene Docker instalado o que Docker no esta en el `PATH`.

## Opcion recomendada: Docker Desktop

1. Abre la guia oficial:
   https://docs.docker.com/desktop/setup/install/windows-install/

2. Descarga e instala Docker Desktop para Windows.

3. Durante la instalacion, usa el backend WSL 2 si el instalador lo ofrece.

4. Reinicia Windows si el instalador lo pide.

5. Abre Docker Desktop desde el menu Inicio.

6. Espera a que Docker Desktop indique que esta corriendo.

7. Abre una nueva terminal PowerShell en esta carpeta:

   ```powershell
   cd C:\Users\camcl\Documents\Codex\2026-06-16\files-mentioned-by-the-user-contexto\outputs\cognifit_entrega_final
   .\deploy.cmd -ResetDb
   ```

## Requisitos importantes

Segun la documentacion oficial de Docker Desktop para Windows:

- Docker Desktop recomienda instalacion por usuario para la mayoria de casos.
- El modo por usuario usa WSL 2 como backend.
- Necesitas Windows 10/11 compatible.
- Necesitas WSL 2 habilitado.
- Necesitas virtualizacion habilitada en BIOS/UEFI.
- Se recomiendan 8 GB de RAM.

## Verificar si ya quedo instalado

En una terminal nueva:

```powershell
docker --version
docker compose version
```

Si ambos comandos responden version, ya puedes desplegar:

```powershell
.\deploy.cmd -ResetDb
```

## Si Docker Desktop abre pero el comando docker no existe

1. Cierra PowerShell.
2. Abre Docker Desktop y espera a que inicie.
3. Abre una nueva terminal.
4. Ejecuta:

   ```powershell
   docker --version
   ```

Si sigue sin existir, reinicia Windows.

## Alternativa sin Docker

Sin Docker tambien se puede correr la API, pero necesitas instalar manualmente:

- Python 3.12
- PostgreSQL 16
- Redis
- Dependencias de `api/requirements.txt`

Para este proyecto, Docker Desktop es la opcion mas simple porque levanta API, DB y Redis juntos con un solo comando.
