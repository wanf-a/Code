from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ModelVersion(Base):
    __tablename__ = "model_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model.id"), index=True, nullable=True)
    version_hash: Mapped[str] = mapped_column(String(64), index=True)
    version_label: Mapped[str] = mapped_column(String(100), default="base")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model = relationship("Model")
