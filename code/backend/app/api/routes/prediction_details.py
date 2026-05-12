from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.prediction_detail import PredictionDetail
from app.schemas.common import Paginated
from app.schemas.prediction_detail import PredictionDetailOut
from app.utils.pagination import paginate

router = APIRouter(prefix="/plans/{plan_id}/details", tags=["prediction-details"])


@router.get("", response_model=Paginated[PredictionDetailOut])
def list_prediction_details(
    plan_id: int,
    page: int = 1,
    size: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[PredictionDetailOut]:
    query = db.query(PredictionDetail).filter(PredictionDetail.plan_id == plan_id)
    if start_time:
        query = query.filter(PredictionDetail.record_time >= start_time)
    if end_time:
        query = query.filter(PredictionDetail.record_time <= end_time)
    total, items = paginate(query.order_by(PredictionDetail.record_time.asc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)
