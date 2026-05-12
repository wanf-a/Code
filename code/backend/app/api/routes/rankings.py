from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.prediction_detail import PredictionDetail
from app.models.ranking import Ranking
from app.schemas.common import Paginated
from app.schemas.ranking import RankingOut, RankingSummaryOut
from app.services.ranking_service import calculate_ranking_summary
from app.utils.pagination import paginate

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("", response_model=Paginated[RankingOut])

def list_rankings(
    page: int = 1,
    size: int = 20,
    rank_type: Optional[str] = None,
    weather: Optional[str] = None,
    is_holiday: Optional[bool] = None,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[RankingOut]:
    query = db.query(Ranking)
    if rank_type:
        query = query.filter(Ranking.rank_type == rank_type)
    if weather:
        query = query.filter(Ranking.weather == weather)
    if is_holiday is not None:
        query = query.filter(Ranking.is_holiday == int(is_holiday))
    if model_name:
        query = query.filter(Ranking.model_name.contains(model_name))
    total, items = paginate(query.order_by(Ranking.id.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.get("/summary", response_model=list[RankingSummaryOut])
def get_ranking_summary(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    model_name: Optional[str] = None,
    rank_type: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> list[RankingSummaryOut]:
    if source == "epf":
        return calculate_ranking_summary(
            db,
            start_time=start_time,
            end_time=end_time,
            model_name=model_name,
            rank_type=rank_type,
            source=source,
        )

    if end_time is None or start_time is None:
        latest_record_time = db.query(func.max(PredictionDetail.record_time)).scalar()
        if latest_record_time is None:
            from app.models.prediction_run import PredictionRun as PRun
            latest_record_time = db.query(func.max(PRun.end_time)).filter(
                PRun.status == "completed"
            ).scalar()
        if end_time is None:
            if latest_record_time is not None:
                end_time = latest_record_time
            else:
                return []
        if start_time is None:
            start_time = end_time - timedelta(days=30)

    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time cannot be greater than end_time")

    return calculate_ranking_summary(
        db,
        start_time=start_time,
        end_time=end_time,
        model_name=model_name,
        rank_type=rank_type,
        source=source,
    )

