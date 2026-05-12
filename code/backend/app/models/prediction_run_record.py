from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PredictionRunRecord(Base):
    __tablename__ = "prediction_run_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("prediction_run.id"), index=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    actual_price: Mapped[float] = mapped_column(Numeric(12, 4))
    predicted_price: Mapped[float] = mapped_column(Numeric(12, 4))

    run = relationship("PredictionRun", back_populates="records")
