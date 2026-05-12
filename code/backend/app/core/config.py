from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "power-admin"
    api_v1_prefix: str = "/api"
    server_port: int = 8001
    secret_key: str = "change-this-in-prod"
    access_token_expire_minutes: int = 525600 * 100  # 100 年，永不过期

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_db: str = "dianli"
    mysql_user: str = "root"
    mysql_password: str = "123456"

    upload_dir: str = "storage/uploads"
    cors_origins: List[str] = ["*"]

    # EPF 数据路径配置（支持环境变量覆盖）
    epf_data_path: str = ""  # 如果为空，则使用默认的项目根目录/epf

    # 标签转换阈值配置
    load_low_threshold: int = 40000  # 低负荷阈值
    load_high_threshold: int = 60000  # 高负荷阈值
    wind_low_threshold: float = 4.0  # 微风阈值
    cloud_low_threshold: int = 30  # 晴天阈值
    cloud_high_threshold: int = 70  # 阴天阈值

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()