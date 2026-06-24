param(
    [switch]$ResetDb
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "Docker no esta instalado o no esta en PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para desplegar esta entrega necesitas Docker Desktop:"
    Write-Host "1. Instala Docker Desktop para Windows."
    Write-Host "2. Abre Docker Desktop y espera a que diga que esta corriendo."
    Write-Host "3. Cierra y abre una nueva terminal PowerShell."
    Write-Host "4. Vuelve a ejecutar: .\deploy.cmd -ResetDb"
    Write-Host ""
    Write-Host "Guia incluida: docs\INSTALAR_DOCKER_WINDOWS.md"
    Write-Host "Guia oficial: https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 127
}

try {
    docker compose version | Out-Null
} catch {
    Write-Host ""
    Write-Host "Docker esta instalado, pero 'docker compose' no responde." -ForegroundColor Yellow
    Write-Host "Abre Docker Desktop, espera a que termine de iniciar y vuelve a ejecutar: .\deploy.cmd -ResetDb"
    exit 127
}

if ($ResetDb) {
    Write-Host "Eliminando contenedores y volumenes anteriores..."
    docker compose down -v --remove-orphans
} else {
    docker compose down --remove-orphans
}

Write-Host "Construyendo y levantando API + PostgreSQL + Redis..."
docker compose up -d --build

Write-Host "Esperando a que la API responda..."
$ready = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 3
    }
}

if (-not $ready) {
    docker compose logs --tail=120 api
    throw "La API no respondio a tiempo."
}

Write-Host "Verificando integracion de base de datos..."
docker compose exec -T api python scripts/verify_db_integration.py --database-url "postgresql://cognifit_api:cognifit_api_dev_password@postgres:5432/cognifit"

Write-Host ""
Write-Host "Listo."
Write-Host "Swagger: http://localhost:8000/docs"
Write-Host "Health:  http://localhost:8000/api/v1/health"
Write-Host ""
Write-Host "Para reiniciar la DB desde cero: .\\deploy.ps1 -ResetDb"
