"""预测管理API路由"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.model import Model
from app.models.dataset import Dataset
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResultOut,
    PredictionRecordOut,
    MetricsOut,
)
from app.services.prediction_service import calculate_prediction

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/calculate", response_model=PredictionResultOut)
def calculate_prediction_api(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> PredictionResultOut:
    """
    计算预测结果。
    
    返回Base模型和用户模型的预测值对比，以及统计指标（MAE、RMSE、精度）。
    """
    # 验证模型存在且已训练
    model = db.query(Model).filter(Model.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if model.status != "trained":
        raise HTTPException(status_code=400, detail="模型尚未训练")
    
    # 验证数据集存在
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 验证日期范围
    if request.test_start_date > request.test_end_date:
        raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")
    
    # 计算预测
    result = calculate_prediction(
        db=db,
        model=model,
        dataset_id=request.dataset_id,
        test_start_date=request.test_start_date,
        test_end_date=request.test_end_date,
    )
    
    # 转换为输出格式
    records_out = [
        PredictionRecordOut(
            record_time=r.record_time,
            actual_value=r.actual_value,
            base_model_value=r.base_model_value,
            user_model_value=r.user_model_value,
        )
        for r in result.records
    ]
    
    return PredictionResultOut(
        records=records_out,
        base_model_metrics=MetricsOut(
            mae=result.base_model_metrics.mae,
            rmse=result.base_model_metrics.rmse,
            accuracy=result.base_model_metrics.accuracy,
        ),
        user_model_metrics=MetricsOut(
            mae=result.user_model_metrics.mae,
            rmse=result.user_model_metrics.rmse,
            accuracy=result.user_model_metrics.accuracy,
        ),
    )
