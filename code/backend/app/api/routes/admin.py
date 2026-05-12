from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.security import get_password_hash, verify_password
from app.db.deps import get_db
from app.models.admin import AdminUser
from app.schemas.admin import AdminOut, AdminPasswordUpdate, AdminUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminOut)

def read_me(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return current_admin


@router.put("/me", response_model=AdminOut)

def update_me(
    payload: AdminUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    current_admin.username = payload.username
    current_admin.display_name = payload.display_name
    db.add(current_admin)
    db.commit()
    db.refresh(current_admin)
    return current_admin


@router.put("/me/password")

def update_password(
    payload: AdminPasswordUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    if not verify_password(payload.current_password, current_admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password incorrect")
    current_admin.password_hash = get_password_hash(payload.new_password)
    db.add(current_admin)
    db.commit()
    return {"message": "Password updated"}

