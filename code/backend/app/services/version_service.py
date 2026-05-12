from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dataset_record import DatasetRecord
from app.models.dataset_version import DatasetVersion
from app.models.model import Model
from app.models.model_version import ModelVersion


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_or_create_model_version(db: Session, model_id: int | None) -> ModelVersion:
    if model_id is None:
        base_hash = _sha256_bytes(b"base-week_ahead")
        existing = db.query(ModelVersion).filter(ModelVersion.version_hash == base_hash).first()
        if existing:
            return existing
        version = ModelVersion(model_id=None, version_hash=base_hash, version_label="base-week_ahead")
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    model = db.query(Model).filter(Model.id == model_id).first()
    if not model or not model.file_path:
        return get_or_create_model_version(db, None)

    try:
        with open(model.file_path, "rb") as f:
            file_hash = _sha256_bytes(f.read())
    except FileNotFoundError:
        return get_or_create_model_version(db, None)

    existing = db.query(ModelVersion).filter(ModelVersion.version_hash == file_hash).first()
    if existing:
        return existing

    version = ModelVersion(model_id=model_id, version_hash=file_hash, version_label=model.name)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def get_or_create_dataset_version(db: Session, dataset_id: int) -> DatasetVersion:
    count, min_t, max_t = db.query(
        func.count(DatasetRecord.id),
        func.min(DatasetRecord.record_time),
        func.max(DatasetRecord.record_time),
    ).filter(DatasetRecord.dataset_id == dataset_id).one()

    raw = f"{dataset_id}:{count}:{min_t}:{max_t}".encode("utf-8")
    version_hash = _sha256_bytes(raw)
    existing = db.query(DatasetVersion).filter(DatasetVersion.version_hash == version_hash).first()
    if existing:
        return existing

    time_range = f"{min_t.date() if min_t else 'unknown'}-{max_t.date() if max_t else 'unknown'}"
    version = DatasetVersion(
        dataset_id=dataset_id,
        version_hash=version_hash,
        record_count=int(count or 0),
        time_range=time_range,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
