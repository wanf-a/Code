"""预测服务模块

实现Base模型预测逻辑和预测结果计算。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
import math

from sqlalchemy.orm import Session

from app.models.dataset_record import DatasetRecord
from app.models.model import Model
from app.models.base_price_data import BasePriceData


class PredictionMetrics:
    """预测指标"""
    def __init__(self, mae: float, rmse: float, accuracy: float):
        self.mae = mae
        self.rmse = rmse
        self.accuracy = accuracy


class PredictionRecord:
    """单条预测记录"""
    def __init__(
        self,
        record_time: datetime,
        actual_value: float,
        base_model_value: float,
        user_model_value: float,
    ):
        self.record_time = record_time
        self.actual_value = actual_value
        self.base_model_value = base_model_value
        self.user_model_value = user_model_value


class PredictionResult:
    """预测结果"""
    def __init__(
        self,
        records: list[PredictionRecord],
        base_model_metrics: PredictionMetrics,
        user_model_metrics: PredictionMetrics,
    ):
        self.records = records
        self.base_model_metrics = base_model_metrics
        self.user_model_metrics = user_model_metrics


def get_base_model_prediction(
    db: Session,
    dataset_id: int,
    record_time: datetime,
    prediction_type: str,
) -> Optional[float]:
    """
    获取Base模型的预测值。
    
    Base模型逻辑：
    - 周前预测(week_ahead): 返回前一周同时刻的电价值
    
    Args:
        db: 数据库会话
        dataset_id: 数据集ID
        record_time: 预测时间点
        prediction_type: 预测类型 ('week_ahead')
    
    Returns:
        预测的电价值，如果没有历史数据则返回None
    """
    if prediction_type == "week_ahead":
        # 周前预测：获取前一周同时刻的数据
        lookup_time = record_time - timedelta(weeks=1)
    else:
        return None
    
    # 查找历史记录
    record = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id,
        DatasetRecord.record_time == lookup_time,
    ).first()
    
    if record:
        return float(record.price_kwh)

    base_record = db.query(BasePriceData).filter(
        BasePriceData.record_time == lookup_time,
    ).first()
    if base_record:
        return float(base_record.price_kwh)
    
    return None


def calculate_metrics(
    actual_values: list[float],
    predicted_values: list[float],
) -> PredictionMetrics:
    """
    计算预测指标。
    
    Args:
        actual_values: 实际值列表
        predicted_values: 预测值列表
    
    Returns:
        PredictionMetrics 包含 MAE, RMSE, 精度
    """
    if not actual_values or len(actual_values) != len(predicted_values):
        return PredictionMetrics(mae=0.0, rmse=0.0, accuracy=0.0)
    
    n = len(actual_values)
    
    # 计算MAE (Mean Absolute Error)
    mae = sum(abs(a - p) for a, p in zip(actual_values, predicted_values)) / n
    
    # 计算RMSE (Root Mean Square Error)
    mse = sum((a - p) ** 2 for a, p in zip(actual_values, predicted_values)) / n
    rmse = math.sqrt(mse)
    
    # 计算精度 (1 - MAPE)
    # MAPE = Mean Absolute Percentage Error
    mape_sum = 0.0
    valid_count = 0
    for a, p in zip(actual_values, predicted_values):
        if a != 0:
            mape_sum += abs((a - p) / a)
            valid_count += 1
    
    if valid_count > 0:
        mape = mape_sum / valid_count
        accuracy = max(0.0, (1 - mape) * 100)  # 转换为百分比
    else:
        accuracy = 0.0
    
    return PredictionMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        accuracy=round(accuracy, 2),
    )


def calculate_prediction(
    db: Session,
    model: Model,
    dataset_id: int,
    test_start_date: date,
    test_end_date: date,
) -> PredictionResult:
    """
    计算预测结果。
    
    Args:
        db: 数据库会话
        model: 用户模型
        dataset_id: 数据集ID
        test_start_date: 测试集开始日期
        test_end_date: 测试集结束日期
    
    Returns:
        PredictionResult 包含预测记录和指标
    """
    # 获取测试集数据
    test_records = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id,
        DatasetRecord.record_time >= datetime.combine(test_start_date, datetime.min.time()),
        DatasetRecord.record_time <= datetime.combine(test_end_date, datetime.max.time()),
    ).order_by(DatasetRecord.record_time).all()
    
    prediction_records = []
    actual_values = []
    base_predictions = []
    user_predictions = []
    
    for record in test_records:
        actual_value = float(record.price_kwh)
        
        # Base模型预测
        base_value = get_base_model_prediction(
            db, dataset_id, record.record_time, model.prediction_type
        )
        
        # 用户模型预测 (TODO: 实际调用用户上传的模型)
        # 目前使用简单的模拟：在Base模型基础上加一些随机扰动
        # 实际实现时需要加载并执行用户的Python模型文件
        user_value = base_value if base_value else actual_value
        
        if base_value is not None:
            prediction_records.append(PredictionRecord(
                record_time=record.record_time,
                actual_value=actual_value,
                base_model_value=base_value,
                user_model_value=user_value,
            ))
            actual_values.append(actual_value)
            base_predictions.append(base_value)
            user_predictions.append(user_value)
    
    # 计算指标
    base_metrics = calculate_metrics(actual_values, base_predictions)
    user_metrics = calculate_metrics(actual_values, user_predictions)
    
    return PredictionResult(
        records=prediction_records,
        base_model_metrics=base_metrics,
        user_model_metrics=user_metrics,
    )
