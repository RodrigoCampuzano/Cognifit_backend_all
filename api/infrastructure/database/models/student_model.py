from __future__ import annotations

from sqlalchemy import Boolean, LargeBinary, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class StudentModel(Base):
    __tablename__ = "students"
    __table_args__ = {"schema": "academic"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    group_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    full_name: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    gender: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
