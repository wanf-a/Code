from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RankingOut(BaseModel):
    id: int
    score: float
    time_range: str
    mae_ratio: float
    rmse_ratio: float
    rank_type: str
    weather: str
    is_holiday: bool
    model_name: str
    author: str
    plan_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class RankingSummaryOut(BaseModel):
    plan_id: int
    dataset: str
    type: str
    model: str
    period: str
    load: str
    wind: str
    weather_type: str
    mae: float
    rmse: float
    r2: float
    imape: float
    score: float
    sample_count: int

