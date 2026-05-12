from __future__ import annotations
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_database_url() -> str:
    settings = get_settings()
    return (
        f"mysql+pymysql://{settings.mysql_user}:{quote_plus(settings.mysql_password)}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}?charset=utf8mb4"
    )


def get_engine():
    return create_engine(_build_database_url(), pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

