from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    verify_status: Mapped[str] = mapped_column(String(20), default="未校核")  # 已校核 / 未校核
    created_by: Mapped[int] = mapped_column(ForeignKey("admin_user.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("DatasetFile", back_populates="dataset", cascade="all, delete-orphan")
    records = relationship("DatasetRecord", back_populates="dataset", cascade="all, delete-orphan")

