from __future__ import annotations

from sqlalchemy import Float, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class DiagnosisModel(Base):
    __tablename__ = "diagnoses"
    __table_args__ = {"schema": "diagnosis"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    assignment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    subtype: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(Text)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    feature_vector: Mapped[dict] = mapped_column(JSONB, default=dict)
