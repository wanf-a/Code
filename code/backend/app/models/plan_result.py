from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PlanResult(Base):
    __tablename__ = "plan_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(100))
    weather: Mapped[str] = mapped_column(String(20))
    mae: Mapped[float] = mapped_column(Numeric(12, 3))
    nmae: Mapped[float] = mapped_column(Numeric(12, 3))
    rmse: Mapped[float] = mapped_column(Numeric(12, 3))
    nrmse: Mapped[float] = mapped_column(Numeric(12, 3))
    score: Mapped[float] = mapped_column(Numeric(12, 3))

    plan = relationship("Plan", back_populates="results")

