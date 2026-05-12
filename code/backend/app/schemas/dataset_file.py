from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetFileBase(BaseModel):
    dataset_id: int
    description: Optional[str] = None


class DatasetFileOut(DatasetFileBase):
    id: int
    original_name: str
    stored_path: str
    size_kb: float
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

