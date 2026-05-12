"""天气数据API路由"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.deps import get_db
from app.models.dataset_record import DatasetRecord
from app.api.deps import get_current_admin

router = APIRouter()


@router.get("/daily")
def get_daily_weather(
    dataset_id: int = 2,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取每日聚合天气数据（温度、风速、云量、负荷）"""
    query = db.query(
        func.date(DatasetRecord.record_time).label("date"),
        func.avg(DatasetRecord.temperature).label("avg_temperature"),
        func.avg(DatasetRecord.wind_speed).label("avg_wind_speed"),
        func.avg(DatasetRecord.cloud_cover).label("avg_cloud_cover"),
        func.avg(DatasetRecord.load_kw).label("avg_load"),
    ).filter(DatasetRecord.dataset_id == dataset_id)
    
    if start_time:
        query = query.filter(DatasetRecord.record_time >= start_time)
    if end_time:
        query = query.filter(DatasetRecord.record_time <= end_time)
    
    query = query.group_by(func.date(DatasetRecord.record_time))
    query = query.order_by(func.date(DatasetRecord.record_time))
    
    results = query.all()
    
    items = []
    for row in results:
        cloud = float(row.avg_cloud_cover) if row.avg_cloud_cover else 0
        if cloud <= 30:
            weather_type = "晴"
        elif cloud >= 70:
            weather_type = "阴"
        else:
            weather_type = "多云"
        
        items.append({
            "date": str(row.date),
            "temperature": round(float(row.avg_temperature), 1) if row.avg_temperature else 0,
            "wind_speed": round(float(row.avg_wind_speed), 1) if row.avg_wind_speed else 0,
            "cloud_cover": round(cloud, 1),
            "load": round(float(row.avg_load), 0) if row.avg_load else 0,
            "weather_type": weather_type,
        })
    
    return {"items": items}
