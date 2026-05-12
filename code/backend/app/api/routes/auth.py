from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.deps import get_db
from app.schemas.auth import LoginRequest, Token
from app.services.auth_service import authenticate_admin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    admin = authenticate_admin(db, payload.username, payload.password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    settings = get_settings()
    token = create_access_token(admin.username, timedelta(minutes=settings.access_token_expire_minutes))
    return Token(access_token=token)

'''
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:

    admin = authenticate_admin(db, form_data.username, form_data.password)

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    settings = get_settings()
    token = create_access_token(
        admin.username,
        timedelta(minutes=settings.access_token_expire_minutes)
    )

    return Token(access_token=token)


'''





