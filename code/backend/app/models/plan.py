from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

from app.models.prediction_run import PredictionRun


class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    plan_type: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="未运行")
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("admin_user.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = relationship("PlanResult", back_populates="plan", cascade="all, delete-orphan")
    runs = relationship("PredictionRun", back_populates="plan", cascade="all, delete-orphan")

