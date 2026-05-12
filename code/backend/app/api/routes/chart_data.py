"""图表数据API - 从基础数据表获取数据"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.base_prediction_data import BasePredictionData
from app.models.base_price_data import BasePriceData
from app.models.dataset_record import DatasetRecord
from app.models.tcn_prediction import TcnProbPrediction
from app.models.price_prediction import PricePrediction
from app.models.model import Model as ModelEntity
from app.services.epf_prob_service import filter_epf_prob_rows, load_epf_prob_rows
from app.services.inference_service import has_model_weights, run_inference

router = APIRouter()


@router.get("/prediction")
def get_prediction_chart_data(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取预测图表数据 - 从base_prediction_data表获取预测值，从base_price_data获取负荷"""
    # 从base_prediction_data表获取预测数据
    pred_query = db.query(BasePredictionData)
    if start_time:
        pred_query = pred_query.filter(BasePredictionData.record_time >= start_time)
    if end_time:
        pred_query = pred_query.filter(BasePredictionData.record_time <= end_time)
    
    predictions = pred_query.order_by(BasePredictionData.record_time.asc()).limit(2000).all()
    
    # 构建时间->负荷映射（从base_price_data获取）
    load_map = {}
    if predictions:
        min_time = predictions[0].record_time
        max_time = predictions[-1].record_time
        load_query = db.query(BasePriceData).filter(
            BasePriceData.record_time >= min_time,
            BasePriceData.record_time <= max_time,
        )
        for r in load_query.all():
            load_map[r.record_time] = float(r.load_kw) if r.load_kw else 0
    
    items = []
    for p in predictions:
        items.append({
            "record_time": p.record_time.isoformat() if p.record_time else None,
            "actual_price": float(p.actual_price) if p.actual_price else 0,
            "predicted_price": float(p.predicted_price) if p.predicted_price else 0,
            "load_kw": load_map.get(p.record_time, 0),
        })
    
    return {"items": items, "total": len(items)}


@router.get("/base-records")
def get_base_records(
    page: int = 1,
    size: int = 10,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取基础电价数据 - 用于数据管理页面展示"""
    query = db.query(BasePriceData)
    
    if start_time:
        query = query.filter(BasePriceData.record_time >= start_time)
    if end_time:
        query = query.filter(BasePriceData.record_time <= end_time)
    
    # 获取总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * size
    records = query.order_by(BasePriceData.record_time.desc()).offset(offset).limit(size).all()
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "record_time": r.record_time.isoformat() if r.record_time else None,
            "price_kwh": float(r.price_kwh) if r.price_kwh else 0,
            "load_kw": float(r.load_kw) if r.load_kw else 0,
            "temperature": float(r.temperature) if r.temperature else 0,
            "wind_speed": float(r.wind_speed) if r.wind_speed else 0,
            "cloud_cover": float(r.cloud_cover) if r.cloud_cover else 0,
        })
    
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/weather")
def get_weather_chart_data(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取天气图表数据 - 从base_price_data逐小时返回"""
    query = db.query(BasePriceData)
    
    if start_time:
        query = query.filter(BasePriceData.record_time >= start_time)
    if end_time:
        query = query.filter(BasePriceData.record_time <= end_time)
    
    query = query.order_by(BasePriceData.record_time.asc())
    rows = query.all()
    
    items = []
    for r in rows:
        cloud = float(r.cloud_cover) if r.cloud_cover else 0
        if cloud <= 30:
            weather_type = "晴"
        elif cloud >= 70:
            weather_type = "阴"
        else:
            weather_type = "多云"
        
        items.append({
            "record_time": r.record_time.isoformat() if r.record_time else None,
            "temperature": round(float(r.temperature), 1) if r.temperature else 0,
            "wind_speed": round(float(r.wind_speed), 1) if r.wind_speed else 0,
            "cloud_cover": round(cloud, 1),
            "weather_type": weather_type,
        })
    
    return {"items": items, "total": len(items)}


@router.get("/tcn-probability")
def get_tcn_probability_data(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取TCN概率预测数据"""
    query = db.query(TcnProbPrediction)

    if start_time:
        query = query.filter(TcnProbPrediction.record_time >= start_time)
    if end_time:
        query = query.filter(TcnProbPrediction.record_time <= end_time)

    predictions = query.order_by(TcnProbPrediction.record_time.asc()).limit(5000).all()

    # 构建负荷映射（从base_price_data获取）
    load_map = {}
    if predictions:
        min_time = predictions[0].record_time
        max_time = predictions[-1].record_time
        load_query = db.query(BasePriceData).filter(
            BasePriceData.record_time >= min_time,
            BasePriceData.record_time <= max_time,
        )
        for r in load_query.all():
            hour_key = r.record_time.replace(minute=0, second=0, microsecond=0)
            if hour_key not in load_map:
                load_map[hour_key] = float(r.load_kw) if r.load_kw else 0

    items = []
    for p in predictions:
        items.append({
            "record_time": p.record_time.isoformat() if p.record_time else None,
            "real": float(p.real) if p.real else 0,
            "qr_005": float(p.qr_005) if p.qr_005 else 0,
            "qr_025": float(p.qr_025) if p.qr_025 else 0,
            "qr_05": float(p.qr_05) if p.qr_05 else 0,
            "qr_50": float(p.qr_50) if p.qr_50 else 0,
            "qr_95": float(p.qr_95) if p.qr_95 else 0,
            "qr_975": float(p.qr_975) if p.qr_975 else 0,
            "qr_995": float(p.qr_995) if p.qr_995 else 0,
            "load_kw": load_map.get(p.record_time, 0),
        })

    return {"items": items, "total": len(items)}


@router.get("/epf-probability")
def get_epf_probability_data(
    model: Optional[str] = None,
    model_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Get EPF probability prediction data.

    mode=realtime (default): 使用保存的模型权重进行实时推理
    mode=csv: 从本地 CSV 结果文件读取
    """
    if mode is None:
        mode = "realtime"

    model_name = model
    model_entity = None
    if model_id is not None:
        model_entity = db.query(ModelEntity).filter(ModelEntity.id == model_id).first()
        if not model_entity:
            return {"items": [], "total": 0}
        model_name = model_entity.name
    if not model_name:
        return {"items": [], "total": 0}

    # 实时推理模式（默认）— 无权重时回退到 CSV 模式
    if mode == "realtime" and start_time and end_time and has_model_weights(model_name):

        dataset_id = model_entity.dataset_id if model_entity else None
        if not dataset_id:
            from app.models.dataset import Dataset
            ds = db.query(Dataset).first()
            dataset_id = ds.id if ds else None
        if not dataset_id:
            return {"items": [], "total": 0, "error": "未找到数据集"}

        try:
            rows = run_inference(
                db=db,
                model_name=model_name,
                dataset_id=dataset_id,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            return {"items": [], "total": 0, "error": f"实时推理失败: {str(e)}"}

        times = [row["record_time"] for row in rows]
        load_map = {}
        if times:
            load_query = db.query(
                BasePriceData.record_time, BasePriceData.load_kw
            ).filter(BasePriceData.record_time.in_(times))
            for r in load_query.all():
                load_map[r.record_time] = float(r.load_kw) if r.load_kw else 0.0

        items = []
        for row in rows:
            ts = row["record_time"]
            items.append({
                "record_time": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "real": float(row.get("real", 0.0)),
                "qr_005": float(row.get("qr_005", 0.0)),
                "qr_025": float(row.get("qr_025", 0.0)),
                "qr_05": float(row.get("qr_05", 0.0)),
                "qr_50": float(row.get("qr_50", 0.0)),
                "qr_95": float(row.get("qr_95", 0.0)),
                "qr_975": float(row.get("qr_975", 0.0)),
                "qr_995": float(row.get("qr_995", 0.0)),
                "load_kw": load_map.get(ts, 0.0),
            })

        return {"items": items, "total": len(items), "mode": "realtime"}

    # CSV 模式（无权重文件时也自动回退到此模式）
    try:
        rows, _ = load_epf_prob_rows(model_name, start_time=start_time, end_time=end_time, prefer_week=False)
    except (ValueError, FileNotFoundError):
        rows = []
    if not rows:
        return {"items": [], "total": 0, "error": "未找到预测数据，请先训练模型"}

    times = [row["record_time"] for row in rows if isinstance(row.get("record_time"), datetime)]
    load_map = {}
    if times:
        load_query = db.query(BasePriceData.record_time, BasePriceData.load_kw).filter(
            BasePriceData.record_time.in_(times),
        )
        for r in load_query.all():
            load_map[r.record_time] = float(r.load_kw) if r.load_kw else 0.0

    items = []
    for row in rows:
        ts = row.get("record_time")
        if not isinstance(ts, datetime):
            continue
        items.append({
            "record_time": ts.isoformat(),
            "real": float(row.get("real", 0.0)),
            "qr_005": float(row.get("qr_005", 0.0)),
            "qr_025": float(row.get("qr_025", 0.0)),
            "qr_05": float(row.get("qr_05", 0.0)),
            "qr_50": float(row.get("qr_50", 0.0)),
            "qr_95": float(row.get("qr_95", 0.0)),
            "qr_975": float(row.get("qr_975", 0.0)),
            "qr_995": float(row.get("qr_995", 0.0)),
            "load_kw": load_map.get(ts, 0.0),
        })

    return {"items": items, "total": len(items), "mode": "csv"}
