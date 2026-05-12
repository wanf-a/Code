from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.base_price_data import BasePriceData
from app.models.dataset_record import DatasetRecord
from app.models.plan import Plan
from app.models.prediction_run import PredictionRun
from app.models.prediction_run_record import PredictionRunRecord
from app.schemas.common import Paginated
from app.schemas.prediction_run import (
    PredictionRunCreate,
    PredictionRunOut,
    PredictionRunRecordOut,
)
from app.services.run_executor import execute_prediction_run
from app.core.config import get_settings
from app.utils.pagination import paginate

router = APIRouter(prefix="/plans/{plan_id}/runs", tags=["prediction-runs"])


@router.get("", response_model=Paginated[PredictionRunOut])
def list_runs(
    plan_id: int,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[PredictionRunOut]:
    query = db.query(PredictionRun).filter(PredictionRun.plan_id == plan_id)
    total, items = paginate(query.order_by(PredictionRun.created_at.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.get("/latest", response_model=PredictionRunOut)
def get_latest_run(
    plan_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> PredictionRunOut:
    run = (
        db.query(PredictionRun)
        .filter(PredictionRun.plan_id == plan_id)
        .order_by(PredictionRun.created_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No prediction runs found.")
    return run


@router.post("", response_model=PredictionRunOut)
def create_run(
    plan_id: int,
    payload: PredictionRunCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> PredictionRunOut:
    try:
        run = execute_prediction_run(
            db,
            plan_id=plan_id,
            model_id=payload.model_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            settings=get_settings(),
        )
        return run
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{run_id}/records", response_model=Paginated[PredictionRunRecordOut])
def list_run_records(
    plan_id: int,
    run_id: int,
    page: int = 1,
    size: int = 200,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[PredictionRunRecordOut]:
    run = db.query(PredictionRun).filter(
        PredictionRun.id == run_id,
        PredictionRun.plan_id == plan_id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    query = db.query(PredictionRunRecord).filter(PredictionRunRecord.run_id == run_id)
    if start_time:
        query = query.filter(PredictionRunRecord.record_time >= start_time)
    if end_time:
        query = query.filter(PredictionRunRecord.record_time <= end_time)

    total, items = paginate(query.order_by(PredictionRunRecord.record_time.asc()), page, size)

    load_map = {}
    if items:
        times = [item.record_time for item in items]
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        dataset_id = plan.dataset_id if plan else None
        ds_query = db.query(DatasetRecord.record_time, DatasetRecord.load_kw).filter(
            DatasetRecord.dataset_id == dataset_id,
            DatasetRecord.record_time.in_(times),
        )
        for row in ds_query.all():
            load_map[row.record_time] = float(row.load_kw) if row.load_kw else 0.0

        if len(load_map) < len(times):
            base_query = db.query(BasePriceData.record_time, BasePriceData.load_kw).filter(
                BasePriceData.record_time.in_(times),
            )
            for row in base_query.all():
                if row.record_time not in load_map:
                    load_map[row.record_time] = float(row.load_kw) if row.load_kw else 0.0

    output = []
    for item in items:
        output.append(
            PredictionRunRecordOut(
                id=item.id,
                run_id=item.run_id,
                record_time=item.record_time,
                actual_price=float(item.actual_price),
                predicted_price=float(item.predicted_price),
                load_kw=load_map.get(item.record_time, 0.0),
            )
        )

    return Paginated(total=total, items=output, page=page, size=size)
