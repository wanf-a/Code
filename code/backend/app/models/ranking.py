from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Ranking(Base):
    __tablename__ = "ranking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[float] = mapped_column(Numeric(12, 3))
    time_range: Mapped[str] = mapped_column(String(60))
    mae_ratio: Mapped[float] = mapped_column(Numeric(12, 3))
    rmse_ratio: Mapped[float] = mapped_column(Numeric(12, 3))
    rank_type: Mapped[str] = mapped_column(String(20))
    weather: Mapped[str] = mapped_column(String(20))
    is_holiday: Mapped[bool] = mapped_column(Integer, default=0)
    model_name: Mapped[str] = mapped_column(String(100))
    author: Mapped[str] = mapped_column(String(50))
    plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("plan.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

