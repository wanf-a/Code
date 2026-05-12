from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DatasetFile(Base):
    __tablename__ = "dataset_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(255))
    size_kb: Mapped[float] = mapped_column(Numeric(12, 2))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("admin_user.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="files")

