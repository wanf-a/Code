from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TcnProbPrediction(Base):
    __tablename__ = "tcn_prob_prediction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    real: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_005: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_025: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_05: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_50: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_95: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_975: Mapped[float] = mapped_column(Numeric(12, 4))
    qr_995: Mapped[float] = mapped_column(Numeric(12, 4))
