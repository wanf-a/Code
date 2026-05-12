from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BasePredictionData(Base):
    """基础预测数据表 - 存储预测结果数据，用于图表展示"""
    __tablename__ = "base_prediction_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_time: Mapped[datetime] = mapped_column(DateTime, index=True, unique=True)
    actual_price: Mapped[float] = mapped_column(Numeric(12, 4))
    predicted_price: Mapped[float] = mapped_column(Numeric(12, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
