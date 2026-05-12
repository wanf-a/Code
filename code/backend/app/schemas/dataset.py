from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(DatasetBase):
    pass


class DatasetOut(DatasetBase):
    id: int
    verify_status: str = "未校核"
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

