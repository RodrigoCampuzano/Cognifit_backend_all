#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo ""
  echo "Docker no esta instalado o no esta en PATH."
  echo ""
  echo "Instala Docker Desktop, abrelo, espera a que este corriendo y vuelve a ejecutar:"
  echo "./deploy.sh --reset-db"
  echo ""
  echo "Guia incluida: docs/INSTALAR_DOCKER_WINDOWS.md"
  echo "Guia oficial: https://docs.docker.com/desktop/setup/install/windows-install/"
  exit 127
fi

if ! docker compose version >/dev/null 2>&1; then
  echo ""
  echo "Docker esta instalado, pero 'docker compose' no responde."
  echo "Abre Docker Desktop, espera a que termine de iniciar y vuelve a ejecutar: ./deploy.sh --reset-db"
  exit 127
fi

RESET_DB="${1:-}"
if [[ "$RESET_DB" == "--reset-db" ]]; then
  echo "Eliminando contenedores y volumenes anteriores..."
  docker compose down -v --remove-orphans
else
  docker compose down --remove-orphans
fi

echo "Construyendo y levantando API + PostgreSQL + Redis..."
docker compose up -d --build

echo "Esperando a que la API responda..."
for i in {1..60}; do
  if curl -fsS "http://localhost:8000/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
  if [[ "$i" == "60" ]]; then
    docker compose logs --tail=120 api
    echo "La API no respondio a tiempo." >&2
    exit 1
  fi
done

echo "Verificando integracion de base de datos..."
docker compose exec -T api python scripts/verify_db_integration.py --database-url "postgresql://cognifit_api:cognifit_api_dev_password@postgres:5432/cognifit"

echo ""
echo "Listo."
echo "Swagger: http://localhost:8000/docs"
echo "Health:  http://localhost:8000/api/v1/health"
echo ""
echo "Para reiniciar la DB desde cero: ./deploy.sh --reset-db"
