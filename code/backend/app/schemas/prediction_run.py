from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionRunCreate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    model_id: Optional[int] = None


class PredictionRunOut(BaseModel):
    id: int
    plan_id: int
    model_id: Optional[int]
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    record_count: int
    mae: Optional[float]
    rmse: Optional[float]
    r2: Optional[float]
    imape: Optional[float]
    score: Optional[float]
    message: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class PredictionRunRecordOut(BaseModel):
    id: int
    run_id: int
    record_time: datetime
    actual_price: float
    predicted_price: float
    load_kw: float = 0.0

    class Config:
        from_attributes = True
