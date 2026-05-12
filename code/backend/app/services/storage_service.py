from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.core.config import get_settings


def ensure_upload_dir() -> Path:
    settings = get_settings()
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def save_upload_file(file_bytes: bytes, original_name: str) -> tuple[str, str]:
    settings = get_settings()
    upload_path = ensure_upload_dir()
    suffix = Path(original_name).suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = upload_path / stored_name
    stored_path.write_bytes(file_bytes)
    relative_path = os.path.join(settings.upload_dir, stored_name)
    return stored_name, relative_path


def delete_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass

