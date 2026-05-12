from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.services.init_db import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def read_root() -> dict:
    return {"message": "ok"}


def run_server():
    """启动服务器的入口函数"""
    uvicorn.run(
        "app.main:app",
        host=getattr(settings, 'server_host', '0.0.0.0'),
        port=settings.server_port,
        reload=False,
    )

