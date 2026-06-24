from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgModelVersionRepository:
    """Gestión de versiones del modelo de ML (HU-BK-13 / HU-MD-11)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_versions(self) -> list[dict]:
        result = await self.session.execute(
            text(
                '''
                SELECT id, version_tag, algorithm, accuracy, f1_score, precision_score, recall_score,
                       f1_macro_subtype, f1_macro_severity, balanced_accuracy, sensitivity_high_risk,
                       is_production, train_date, created_at, notes
                FROM diagnosis.ml_model_versions
                ORDER BY is_production DESC, train_date DESC, created_at DESC
                '''
            )
        )
        return [dict(r) for r in result.mappings().all()]

    async def get_production(self) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                SELECT id, version_tag, algorithm, f1_macro_subtype, f1_macro_severity,
                       balanced_accuracy, sensitivity_high_risk, train_date
                FROM diagnosis.ml_model_versions WHERE is_production ORDER BY train_date DESC LIMIT 1
                '''
            )
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def activate(self, version_tag: str) -> dict:
        """Marca una versión como producción. El constraint ck_model_production_thresholds
        bloquea a nivel DB activar un modelo sin métricas validadas (lanza IntegrityError)."""
        exists = await self.session.execute(
            text("SELECT 1 FROM diagnosis.ml_model_versions WHERE version_tag = :tag"),
            {"tag": version_tag},
        )
        if not exists.first():
            raise ValueError(f"Versión '{version_tag}' no existe")
        # Desactivar todas y activar la objetivo (el CHECK valida umbrales mínimos).
        await self.session.execute(
            text("UPDATE diagnosis.ml_model_versions SET is_production = FALSE WHERE is_production")
        )
        result = await self.session.execute(
            text(
                '''
                UPDATE diagnosis.ml_model_versions SET is_production = TRUE
                WHERE version_tag = :tag
                RETURNING id, version_tag, is_production, f1_macro_subtype, f1_macro_severity,
                          balanced_accuracy, sensitivity_high_risk
                '''
            ),
            {"tag": version_tag},
        )
        return dict(result.mappings().one())
