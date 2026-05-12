from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetRecordBase(BaseModel):
    record_time: datetime
    price_kwh: float
    generation_kwh: float
    load_kw: float
    weather_type: str
    temperature: Optional[float] = None
    wind_speed: Optional[float] = None
    cloud_cover: Optional[float] = None
    is_holiday: bool = False


class DatasetRecordCreate(DatasetRecordBase):
    pass


class DatasetRecordOut(DatasetRecordBase):
    id: int
    dataset_id: int
    created_at: datetime

    class Config:
        from_attributes = True

