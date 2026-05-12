from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.plan_result import PlanResult
from app.schemas.plan_result import PlanResultOut

router = APIRouter(prefix="/plans/{plan_id}/results", tags=["plan-results"])


@router.get("", response_model=List[PlanResultOut])

def list_results(
    plan_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> List[PlanResult]:
    return db.query(PlanResult).filter(PlanResult.plan_id == plan_id).all()

