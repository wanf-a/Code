from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.admin import AdminUser


def authenticate_admin(db: Session, username: str, password: str) -> Optional[AdminUser]:
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin

