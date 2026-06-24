from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import get_db
from api.dependencies.services import get_diagnosis_client, get_recommendation_client
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
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
):
    """Estado agregado de los microservicios PLN (monitoreo admin)."""
    diagnosis = await diagnosis_client.health()
    recommendation = await recommendation_client.health()
    all_ok = diagnosis.get("status") == "ok" and recommendation.get("status") == "ok"
    return {"status": "ok" if all_ok else "degraded", "diagnosis": diagnosis, "recommendation": recommendation}
