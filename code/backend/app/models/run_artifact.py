from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RunArtifact(Base):
    __tablename__ = "run_artifact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("prediction_run.id"), index=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_version.id"), index=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_version.id"), index=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    case_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_root: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_root: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("PredictionRun")
    model_version = relationship("ModelVersion")
    dataset_version = relationship("DatasetVersion")
