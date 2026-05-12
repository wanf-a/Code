from __future__ import annotations

import os
import re
import uuid
import json
import zipfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.db.deps import get_db
from app.models.dataset import Dataset
from app.models.model import Model
from app.models.task import Task
from app.models.task_log import TaskLog
from app.schemas.common import Paginated
from app.schemas.model import (
    EpfAutoTrainResponse,
    EpfCandidateOut,
    ModelOut,
    ModelTrainResponse,
    ModelTrainTaskResponse,
)
from app.services.epf_model_selector import load_epf_model_metrics, score_epf_metrics, select_best_epf_model
from app.services.storage_service import delete_file, save_upload_file
from app.services.task_service import execute_task
from app.services.training_service import latest_trained_file, trained_model_dir
from app.utils.pagination import paginate

router = APIRouter(prefix="/models", tags=["models"])

EPF_SEED_MODELS = [
    ("TCN周前概率", "EPF TCN 概率预测"),
    ("Mamba周前概率", "EPF Mamba 概率预测"),
    ("NLinear周前概率", "EPF NLinear 概率预测"),
    ("集成周前概率", "EPF Ensemble 概率预测"),
]


def _to_model_out(model: Model, dataset: Optional[Dataset] = None) -> ModelOut:
    dataset = dataset or model.dataset
    return ModelOut(
        id=model.id,
        name=model.name,
        description=model.description,
        file_path=model.file_path,
        original_name=model.original_name,
        dataset_id=model.dataset_id,
        dataset_name=dataset.name if dataset else None,
        verify_status=dataset.verify_status if dataset else None,
        train_start_date=model.train_start_date,
        train_end_date=model.train_end_date,
        prediction_type=model.prediction_type,
        status=model.status,
        trained_at=model.trained_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("", response_model=Paginated[ModelOut])
def list_models(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[ModelOut]:
    query = db.query(Model)
    if keyword:
        query = query.filter(Model.name.contains(keyword))
    if status:
        query = query.filter(Model.status == status)
    total, items = paginate(query.order_by(Model.id.desc()), page, size)
    dataset_ids = list({item.dataset_id for item in items})
    datasets = (
        db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
        if dataset_ids
        else []
    )
    dataset_map = {dataset.id: dataset for dataset in datasets}
    model_items = [_to_model_out(item, dataset_map.get(item.dataset_id)) for item in items]
    return Paginated(total=total, items=model_items, page=page, size=size)


@router.post("/upload", response_model=ModelOut)
def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    dataset_id: int = Form(...),
    train_start_date: str = Form(...),
    train_end_date: str = Form(...),
    prediction_type: str = Form(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> ModelOut:
    normalized_name = (name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Model name is required.")
    if not (file.filename or "").endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python model files (.py) are supported.")

    if prediction_type != "week_ahead":
        raise HTTPException(status_code=400, detail="Only week_ahead is supported.")

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Dataset not found.")

    try:
        start_date = date.fromisoformat(train_start_date)
        end_date = date.fromisoformat(train_end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid training date.") from exc
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Training start date cannot be after end date.")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded model file is empty.")

    _, stored_path = save_upload_file(content, file.filename or "model.py")

    model = Model(
        name=normalized_name,
        description=description,
        file_path=stored_path,
        original_name=file.filename or "model.py",
        dataset_id=dataset_id,
        train_start_date=start_date,
        train_end_date=end_date,
        prediction_type=prediction_type,
        status="untrained",
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _to_model_out(model, dataset)


@router.post("/seed-epf")
def seed_epf_models(
    dataset_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict:
    if dataset_id is not None:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    else:
        dataset = db.query(Dataset).filter(Dataset.name == "广东电价数据").first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Dataset not found for EPF seed.")

    created = 0
    existing = 0
    items = []
    for name, desc in EPF_SEED_MODELS:
        model = db.query(Model).filter(Model.name == name, Model.dataset_id == dataset.id).first()
        if model:
            existing += 1
        else:
            model = Model(
                name=name,
                description=desc,
                file_path="epf_stub.py",
                original_name="epf_stub.py",
                dataset_id=dataset.id,
                train_start_date=date(2024, 1, 1),
                train_end_date=date(2024, 12, 31),
                prediction_type="week_ahead",
                status="untrained",
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            created += 1
        items.append({"id": model.id, "name": model.name})

    return {
        "dataset_id": dataset.id,
        "created": created,
        "existing": existing,
        "items": items,
    }


def _sanitize_model_name(model_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", "_", model_name).strip("_")
    return sanitized or "model"


def _trained_model_dir(model_name: str) -> Path:
    return trained_model_dir(model_name, get_settings())


def _match_epf_folder(model_name: str) -> Optional[str]:
    name = model_name.lower()
    if "ensemble" in name or "集成" in model_name:
        return "ensemble"
    if "mamba" in name:
        return "mamba"
    if "nlinear" in name:
        return "nlinear"
    if "tcn" in name:
        return "tcn"
    return None


def _latest_epf_results_json(model_name: str) -> Optional[Path]:
    folder = _match_epf_folder(model_name)
    if not folder:
        return None
    root = Path(__file__).resolve().parents[4] / "epf" / folder
    candidates = list(root.glob("results/**/results.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


TRAIN_TASK_STALE_MINUTES = 300


def _is_stale_training_task(task: Task, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    reference_time = task.started_at or task.created_at
    if not reference_time:
        return False
    return reference_time < now - timedelta(minutes=TRAIN_TASK_STALE_MINUTES)


def _mark_task_failed(db: Session, task: Task, reason: str) -> None:
    task.status = "failed"
    task.last_error = reason[:200]
    task.finished_at = datetime.utcnow()
    db.add(task)
    db.add(TaskLog(task_id=task.id, level="error", message=reason[:500]))
    db.commit()


@router.post("/trained-files/upload")
def upload_trained_file(
    model_name: str = Form(...),
    file: UploadFile = File(...),
    _admin=Depends(get_current_admin),
) -> dict:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_name = file.filename or "trained_model.bin"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stored_name = f"{timestamp}_{uuid.uuid4().hex}_{file_name}"
    target_path = _trained_model_dir(model_name) / stored_name
    target_path.write_bytes(content)

    return {
        "message": "Trained file uploaded.",
        "model_name": model_name,
        "stored_name": stored_name,
    }


@router.get("/trained-files/download")
def download_trained_file(
    model_name: str,
    _admin=Depends(get_current_admin),
) -> FileResponse:
    latest_uploaded = latest_trained_file(model_name, get_settings())
    if latest_uploaded:
        return FileResponse(str(latest_uploaded), filename=latest_uploaded.name)

    fallback = _latest_epf_results_json(model_name)
    if fallback and fallback.exists():
        return FileResponse(str(fallback), filename=f"{_sanitize_model_name(model_name)}_latest_results.json")

    raise HTTPException(
        status_code=404,
        detail="No trained file found for this model. Please upload one first.",
    )


@router.post("/auto-train", response_model=EpfAutoTrainResponse)
def auto_train_with_epf(
    _admin=Depends(get_current_admin),
) -> EpfAutoTrainResponse:
    """
    Evaluate EPF model outputs with weighted metrics and automatically select
    the best model.
    """
    try:
        selection = select_best_epf_model()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    candidates = [
        EpfCandidateOut(
            model_name=item.model_name,
            score=item.score,
            mape_150=item.metrics["MAPE_150"],
            mae=item.metrics["MAE"],
            rmse=item.metrics["RMSE"],
            r2=item.metrics["R2"],
            source_file=item.source_file,
        )
        for item in selection.candidates
    ]

    return EpfAutoTrainResponse(
        selected_model=selection.selected_model,
        selected_score=selection.selected_score,
        retrained=selection.retrained,
        used_cache=selection.used_cache,
        candidates=candidates,
        message=(
            f"Best model: {selection.selected_model}. "
            f"{selection.detail}"
        ),
    )


@router.get("/{model_id}", response_model=ModelOut)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> ModelOut:
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found.")
    dataset = db.query(Dataset).filter(Dataset.id == model.dataset_id).first()
    return _to_model_out(model, dataset)


def _execute_task_background(task_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            execute_task(db, task)
    finally:
        db.close()


@router.post("/{model_id}/train", response_model=ModelTrainTaskResponse)
def train_model(
    model_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> ModelTrainTaskResponse:
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found.")

    dataset = db.query(Dataset).filter(Dataset.id == model.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Dataset not found for model.")

    running = (
        db.query(Task)
        .filter(Task.task_type == "model_train", Task.status.in_(["queued", "running"]))
        .all()
    )
    for task in running:
        try:
            payload = json.loads(task.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        try:
            queued_model_id = int(payload.get("model_id") or 0)
        except (TypeError, ValueError):
            _mark_task_failed(db, task, "Invalid training task payload: model_id is missing or malformed.")
            continue
        if queued_model_id == model.id:
            if _is_stale_training_task(task):
                _mark_task_failed(db, task, "Marked stale after backend restart or abandoned execution.")
                continue
            return ModelTrainTaskResponse(
                id=model.id,
                status=model.status,
                trained_at=model.trained_at,
                task_id=task.id,
                message="Training task is already queued or running.",
            )

    task = Task(
        task_type="model_train",
        status="queued",
        payload_json=json.dumps({"model_id": model.id}, ensure_ascii=False),
        max_retries=1,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background.add_task(_execute_task_background, task.id)
    return ModelTrainTaskResponse(
        id=model.id,
        status=model.status,
        trained_at=model.trained_at,
        task_id=task.id,
        message="Training task submitted.",
    )


@router.post("/{model_id}/upload-weights")
def upload_model_weights(
    model_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict:
    """上传模型权重文件（zip 包含 model_weights.pt / scalers.pkl / model_config.json）"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found.")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    if not zipfile.is_zipfile(BytesIO(content)):
        raise HTTPException(status_code=400, detail="请上传 ZIP 格式的文件")

    zf = zipfile.ZipFile(BytesIO(content))
    names = zf.namelist()

    weight_files = [
        n for n in names
        if not n.endswith("/")
        and (Path(n).name == "model_weights.pt"
             or (Path(n).name.startswith("model_weights_") and n.endswith(".pt")))
    ]
    if not weight_files:
        raise HTTPException(
            status_code=400,
            detail="ZIP 文件中未找到 model_weights.pt 或 model_weights_*.pt 权重文件",
        )

    weight_parent = str(Path(weight_files[0]).parent)
    if weight_parent == ".":
        weight_parent = ""

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    target_dir = trained_model_dir(model.name, get_settings()) / run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    extracted = []
    for member in names:
        if member.endswith("/"):
            continue
        member_parent = str(Path(member).parent)
        if member_parent == weight_parent or (weight_parent == "" and "/" not in member):
            filename = Path(member).name
            (target_dir / filename).write_bytes(zf.read(member))
            extracted.append(filename)

    warnings = []
    if "scalers.pkl" not in extracted:
        warnings.append("缺少 scalers.pkl，实时推理可能失败")
    if "model_config.json" not in extracted:
        warnings.append("缺少 model_config.json，实时推理可能失败")

    model.status = "trained"
    model.trained_at = datetime.utcnow()
    db.add(model)
    db.commit()

    return {
        "message": "权重文件上传成功",
        "model_id": model.id,
        "model_name": model.name,
        "status": "trained",
        "extracted_files": extracted,
        "warnings": warnings,
    }


def _append_auto_selection_note(
    description: Optional[str],
    selected_model: str,
    selected_score: float,
) -> str:
    note = f"[EPF_AUTO_SELECTED] {selected_model} (score={selected_score:.6f})"
    if not description:
        return note

    cleaned_lines = [
        line
        for line in description.splitlines()
        if not line.strip().startswith("[EPF_AUTO_SELECTED]")
    ]
    cleaned_lines.append(note)
    return "\n".join(cleaned_lines)


@router.delete("/{model_id}")
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict:
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found.")

    delete_file(model.file_path)
    db.delete(model)
    db.commit()
    return {"message": "Deleted"}
