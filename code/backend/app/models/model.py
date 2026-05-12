from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Model(Base):
    """预测模型表"""
    __tablename__ = "model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), index=True)
    train_start_date: Mapped[date] = mapped_column(Date)
    train_end_date: Mapped[date] = mapped_column(Date)
    prediction_type: Mapped[str] = mapped_column(
        Enum("day_ahead", "week_ahead", name="prediction_type_enum"),
        default="week_ahead"
    )
    status: Mapped[str] = mapped_column(
        Enum("untrained", "trained", name="model_status_enum"),
        default="untrained"
    )
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("Dataset", backref="models")
