from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    total: int
    items: List[T]
    page: int
    size: int


class Message(BaseModel):
    message: str


class PageParams(BaseModel):
    page: int = 1
    size: int = 20
    keyword: Optional[str] = None

