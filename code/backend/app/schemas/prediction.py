"""预测相关的Schema定义"""
from __future__ import annotations

from datetime import date, datetime
from typing import List

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """预测计算请求"""
    model_id: int
    dataset_id: int
    test_start_date: date
    test_end_date: date


class MetricsOut(BaseModel):
    """预测指标输出"""
    mae: float
    rmse: float
    accuracy: float


class PredictionRecordOut(BaseModel):
    """单条预测记录输出"""
    record_time: datetime
    actual_value: float
    base_model_value: float
    user_model_value: float


class PredictionResultOut(BaseModel):
    """预测结果输出"""
    records: List[PredictionRecordOut]
    base_model_metrics: MetricsOut
    user_model_metrics: MetricsOut
