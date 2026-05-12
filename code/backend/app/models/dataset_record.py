from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DatasetRecord(Base):
    __tablename__ = "dataset_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), index=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    price_kwh: Mapped[float] = mapped_column(Numeric(12, 4))
    generation_kwh: Mapped[float] = mapped_column(Numeric(12, 2))
    load_kw: Mapped[float] = mapped_column(Numeric(12, 4))
    weather_type: Mapped[str] = mapped_column(String(20))
    temperature: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)
    wind_speed: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)
    cloud_cover: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)
    is_holiday: Mapped[bool] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="records")

