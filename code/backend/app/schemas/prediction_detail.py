from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class PredictionDetailOut(BaseModel):
    id: int
    plan_id: int
    record_time: datetime
    actual_price: float
    predicted_price: float

    class Config:
        from_attributes = True
