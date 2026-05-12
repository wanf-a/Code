from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PredictionDetail(Base):
    __tablename__ = "prediction_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), index=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    actual_price: Mapped[float] = mapped_column(Numeric(12, 4))
    predicted_price: Mapped[float] = mapped_column(Numeric(12, 4))

    plan = relationship("Plan", backref="prediction_details")
