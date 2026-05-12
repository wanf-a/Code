from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.base_price_data import BasePriceData
from app.models.dataset_record import DatasetRecord
from app.schemas.common import Paginated
from app.schemas.dataset_record import DatasetRecordCreate, DatasetRecordOut
from app.utils.pagination import paginate

router = APIRouter(prefix="/datasets/{dataset_id}/records", tags=["dataset-records"])


@router.get("", response_model=Paginated[DatasetRecordOut])

def list_records(
    dataset_id: int,
    page: int = 1,
    size: int = 20,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    weather_type: Optional[str] = None,
    is_holiday: Optional[bool] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[DatasetRecordOut]:
    query = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id)
    if start_time:
        query = query.filter(DatasetRecord.record_time >= start_time)
    if end_time:
        query = query.filter(DatasetRecord.record_time <= end_time)
    if weather_type:
        query = query.filter(DatasetRecord.weather_type == weather_type)
    if is_holiday is not None:
        query = query.filter(DatasetRecord.is_holiday == int(is_holiday))
    total, items = paginate(query.order_by(DatasetRecord.record_time.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.post("", response_model=DatasetRecordOut)

def create_record(
    dataset_id: int,
    payload: DatasetRecordCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> DatasetRecord:
    record = DatasetRecord(dataset_id=dataset_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/range")
def get_records_range(
    dataset_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    # 优先从 base_price_data 获取范围（真实电价数据）
    bp_min, bp_max = db.query(
        func.min(BasePriceData.record_time),
        func.max(BasePriceData.record_time),
    ).one()

    if bp_min and bp_max:
        return {
            "start_time": bp_min.isoformat(),
            "end_time": bp_max.isoformat(),
        }

    # 回退到 dataset_record
    min_t, max_t = db.query(
        func.min(DatasetRecord.record_time),
        func.max(DatasetRecord.record_time),
    ).filter(DatasetRecord.dataset_id == dataset_id).one()
    return {
        "start_time": min_t.isoformat() if min_t else None,
        "end_time": max_t.isoformat() if max_t else None,
    }

