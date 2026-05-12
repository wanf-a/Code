"""Pytest configuration and fixtures."""
from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.main import app
from app.db.deps import get_db
from app.core.security import get_password_hash
from app.models.admin import AdminUser


# 使用SQLite内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db: Session) -> AdminUser:
    """Create a test admin user."""
    admin = AdminUser(
        username="testadmin",
        password_hash=get_password_hash("testpass123"),
        email="test@example.com",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, admin_user: AdminUser) -> dict:
    """Get authentication headers for API requests."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "testpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def temp_upload_dir() -> Generator[str, None, None]:
    """Create a temporary upload directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
