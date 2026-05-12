from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dataset_id: int
    train_start_date: date
    train_end_date: date
    prediction_type: str  # 'week_ahead'


class ModelOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_path: str
    original_name: str
    dataset_id: int
    dataset_name: Optional[str] = None
    verify_status: Optional[str] = None
    train_start_date: date
    train_end_date: date
    prediction_type: str
    status: str
    trained_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelTrainResponse(BaseModel):
    id: int
    status: str
    trained_at: Optional[datetime]
    selected_model: Optional[str] = None
    selected_score: Optional[float] = None
    retrained: Optional[bool] = None
    used_cache: Optional[bool] = None
    message: str


class ModelTrainTaskResponse(BaseModel):
    id: int
    status: str
    trained_at: Optional[datetime]
    task_id: int
    message: str


class EpfCandidateOut(BaseModel):
    model_name: str
    score: float
    mape_150: float
    mae: float
    rmse: float
    r2: float
    source_file: str


class EpfAutoTrainResponse(BaseModel):
    selected_model: str
    selected_score: float
    retrained: bool
    used_cache: bool
    candidates: list[EpfCandidateOut]
    message: str
