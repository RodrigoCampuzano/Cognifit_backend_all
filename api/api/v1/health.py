from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import get_db
from api.dependencies.services import get_diagnosis_client, get_health_registry, get_recommendation_client
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.health_registry import HealthRegistry
from infrastructure.pln.recommendation_client import RecommendationServiceClient

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "cognifit-backend"}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1 AS ok"))
    return {"status": "ok", "db": result.scalar_one()}


@router.get("/health/pln")
async def health_pln(
    diagnosis_client: DiagnosisServiceClient = Depends(get_diagnosis_client),
    recommendation_client: RecommendationServiceClient = Depends(get_recommendation_client),
    registry: HealthRegistry = Depends(get_health_registry),
):
    """Estado agregado de los microservicios PLN (monitoreo admin). Además de
    devolver el estado en vivo, actualiza el registro Singleton consultable
    sin red vía /health/pln/last-known."""
    return await registry.refresh(diagnosis_client, recommendation_client)


@router.get("/health/pln/last-known")
async def health_pln_last_known(registry: HealthRegistry = Depends(get_health_registry)):
    """Último estado conocido sin golpear la red — útil para polling frecuente de dashboards."""
    snapshot = registry.snapshot()
    if snapshot is None:
        raise HTTPException(status_code=503, detail="No health check has run yet")
    return snapshot
