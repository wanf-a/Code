from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/case")
def get_case_config(_admin=Depends(get_current_admin)) -> dict:
    settings = get_settings()
    return {
        "case_id": settings.case_id,
        "case_time": settings.case_time,
        "input_root": settings.input_root,
        "output_root": settings.output_root,
    }
