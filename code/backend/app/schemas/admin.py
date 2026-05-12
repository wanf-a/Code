from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminBase(BaseModel):
    username: str
    display_name: str


class AdminOut(AdminBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminUpdate(BaseModel):
    username: str
    display_name: str


class AdminPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

