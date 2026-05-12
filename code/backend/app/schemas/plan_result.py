from __future__ import annotations

from pydantic import BaseModel


class PlanResultOut(BaseModel):
    id: int
    plan_id: int
    model_name: str
    weather: str
    mae: float
    nmae: float
    rmse: float
    nrmse: float
    score: float

    class Config:
        from_attributes = True

