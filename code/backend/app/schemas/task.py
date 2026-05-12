from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    task_type: str
    payload_json: str
    max_retries: int = 1


class TaskOut(BaseModel):
    id: int
    task_type: str
    status: str
    payload_json: str
    result_json: Optional[str]
    retries: int
    max_retries: int
    last_error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskLogOut(BaseModel):
    id: int
    task_id: int
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
