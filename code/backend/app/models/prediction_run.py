from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PredictionRun(Base):
    __tablename__ = "prediction_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), index=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)

    mae: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    rmse: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    r2: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    imape: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)

    message: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    records = relationship("PredictionRunRecord", back_populates="run", cascade="all, delete-orphan")
    plan = relationship("Plan", back_populates="runs")
