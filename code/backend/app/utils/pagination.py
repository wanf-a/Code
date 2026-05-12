from __future__ import annotations

from typing import Tuple

from sqlalchemy.orm import Query


def paginate(query: Query, page: int, size: int) -> Tuple[int, list]:
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return total, items

