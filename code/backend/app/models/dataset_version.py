from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), index=True)
    version_hash: Mapped[str] = mapped_column(String(64), index=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    time_range: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset")
