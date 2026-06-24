from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class TestSessionModel(Base):
    __tablename__ = "test_sessions"
    __table_args__ = {"schema": "assessment"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    module_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    session_status: Mapped[str] = mapped_column(Text, default="IN_PROGRESS")
    raw_client_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
