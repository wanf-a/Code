from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BasePriceData(Base):
    """基础电价数据表 - 存储标准电价数据，用于校核对比和图表展示"""
    __tablename__ = "base_price_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True, unique=True)
    price_kwh: Mapped[float] = mapped_column(Numeric(12, 4))
    load_kw: Mapped[float] = mapped_column(Numeric(12, 2))
    temperature: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    wind_speed: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    cloud_cover: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
