from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.dataset import Dataset
from app.models.dataset_record import DatasetRecord
from app.models.model import Model
from app.models.task_log import TaskLog


CSV_COLUMNS = [
    ("时间", "record_time"),
    ("电价(元/kWh)", "price_kwh"),
    ("负荷(kW)", "load_kw"),
    ("温度(℃)", "temperature"),
    ("风速(m/s)", "wind_speed"),
    ("云量(%)", "cloud_cover"),
]


def _log(db: Session, task_id: int | None, level: str, message: str) -> None:
    if not task_id:
        return
    db.add(TaskLog(task_id=task_id, level=level, message=message[:500]))
    db.commit()


def sanitize_model_name(model_name: str) -> str:
    safe_chars = []
    for char in model_name.strip():
        if char.isalnum() or char in ("-", "_"):
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    sanitized = "".join(safe_chars).strip("_")
    return sanitized or "model"


def trained_model_dir(model_name: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    base = Path(settings.upload_dir) / "trained_models" / sanitize_model_name(model_name)
    base.mkdir(parents=True, exist_ok=True)
    return base


def latest_trained_file(model_name: str, settings: Settings | None = None) -> Path | None:
    model_dir = trained_model_dir(model_name, settings)
    candidates = [p for p in model_dir.rglob("*") if p.is_file()]
    if not candidates:
        return None
    checkpoint_files = [p for p in candidates if p.name == "checkpoint.zip"]
    return max(checkpoint_files or candidates, key=lambda p: p.stat().st_mtime)


def export_dataset_csv(db: Session, dataset_id: int, target_path: Path) -> int:
    records = (
        db.query(DatasetRecord)
        .filter(DatasetRecord.dataset_id == dataset_id)
        .order_by(DatasetRecord.record_time)
        .all()
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", newline="", encoding="gb18030") as fp:
        writer = csv.writer(fp)
        writer.writerow([label for label, _ in CSV_COLUMNS])
        for record in records:
            writer.writerow(
                [
                    record.record_time.strftime("%Y/%m/%d %H:%M"),
                    float(record.price_kwh or 0),
                    float(record.load_kw or 0),
                    float(record.temperature or 0),
                    float(record.wind_speed or 0),
                    float(record.cloud_cover or 0),
                ]
            )
    return len(records)


def export_model_dataset_csv(
    db: Session,
    model: Model,
    target_path: Path,
) -> int:
    records = (
        db.query(DatasetRecord)
        .filter(
            DatasetRecord.dataset_id == model.dataset_id,
            DatasetRecord.record_time >= datetime.combine(model.train_start_date, datetime.min.time()),
            DatasetRecord.record_time <= datetime.combine(model.train_end_date, datetime.max.time()),
        )
        .order_by(DatasetRecord.record_time)
        .all()
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", newline="", encoding="gb18030") as fp:
        writer = csv.writer(fp)
        writer.writerow([label for label, _ in CSV_COLUMNS])
        for record in records:
            writer.writerow(
                [
                    record.record_time.strftime("%Y/%m/%d %H:%M"),
                    float(record.price_kwh or 0),
                    float(record.load_kw or 0),
                    float(record.temperature or 0),
                    float(record.wind_speed or 0),
                    float(record.cloud_cover or 0),
                ]
            )
    return len(records)


def _parse_metrics(results_path: Path) -> dict[str, Any]:
    if not results_path.exists():
        return {}
    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _create_checkpoint_zip(
    run_dir: Path,
    checkpoint_path: Path,
    manifest: dict[str, Any],
) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    with ZipFile(checkpoint_path, "w", ZIP_DEFLATED) as archive:
        for path in run_dir.rglob("*"):
            if path == checkpoint_path or not path.is_file():
                continue
            archive.write(path, path.relative_to(run_dir).as_posix())


def _resolve_training_python_executable(project_root: Path | None = None) -> str:
    root = project_root or Path(__file__).resolve().parents[2]
    if os.name == "nt":
        candidates = [
            root / ".venv" / "Scripts" / "python.exe",
            root / "venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [
            root / ".venv" / "bin" / "python",
            root / "venv" / "bin" / "python",
        ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    return sys.executable



def _build_training_commands(
    script_path: Path,
    input_csv: Path,
    run_dir: Path,
    python_executable: str | None = None,
) -> list[list[str]]:
    executable = python_executable or _resolve_training_python_executable()
    return [
        [
            executable,
            str(script_path.resolve()),
            "--data",
            str(input_csv.resolve()),
            "--output_dir",
            str(run_dir.resolve()),
            "--batch_size",
            "32",
        ],
        [
            executable,
            str(script_path.resolve()),
            "--data",
            str(input_csv.resolve()),
            "--output_dir",
            str(run_dir.resolve()),
            "--batch_size",
            "16",
            "--input_len",
            "96",
        ],
    ]


def _run_training_process(
    db: Session,
    task_id: int | None,
    script_path: Path,
    input_csv: Path,
    run_dir: Path,
    logs_path: Path,
) -> tuple[int, list[str], datetime, datetime]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    python_executable = _resolve_training_python_executable()
    _log(db, task_id, "info", f"Using Python executable: {python_executable}")
    commands = _build_training_commands(script_path, input_csv, run_dir, python_executable)
    last_tail: list[str] = []
    started_at = datetime.utcnow()
    finished_at = started_at

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    with logs_path.open("w", encoding="utf-8", errors="replace") as logs:
        for index, command in enumerate(commands, start=1):
            _log(db, task_id, "info", f"Starting model script (attempt {index}/{len(commands)}).")
            logs.write("Command: " + " ".join(command) + "\n\n")
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(script_path.resolve().parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=creationflags,
                )
            except FileNotFoundError as exc:
                logs.write(f"Failed to start training command: {exc}\n")
                logs.flush()
                raise RuntimeError(
                    f"Training runtime is unavailable: {exc}. Check the Python environment for this backend."
                ) from exc
            assert process.stdout is not None
            captured_lines: list[str] = []
            for line in process.stdout:
                logs.write(line)
                logs.flush()
                captured_lines.append(line)
                stripped = line.strip()
                if stripped:
                    _log(db, task_id, "info", stripped)
            return_code = process.wait()
            finished_at = datetime.utcnow()
            last_tail = captured_lines[-40:]
            if return_code == 0:
                return return_code, command, started_at, finished_at

            logs.write(f"\n[attempt {index} failed with code {return_code}]\n\n")

    return return_code, commands[-1], started_at, finished_at


def train_uploaded_model(
    db: Session,
    model_id: int,
    task_id: int | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise ValueError("Model not found.")

    dataset = db.query(Dataset).filter(Dataset.id == model.dataset_id).first()
    if not dataset:
        raise ValueError("Dataset not found for model.")

    script_path = Path(model.file_path)
    if not script_path.exists():
        raise ValueError(f"Model script not found: {model.file_path}")

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    model_dir = trained_model_dir(model.name, settings)
    run_dir = model_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    input_csv = run_dir / "input.csv"
    logs_path = run_dir / "logs.txt"

    _log(
        db,
        task_id,
        "info",
        f"Exporting dataset #{dataset.id} to CSV for training range {model.train_start_date} to {model.train_end_date}.",
    )
    record_count = export_model_dataset_csv(db, model, input_csv)
    if record_count == 0:
        raise ValueError("Dataset has no records to train with.")

    return_code, command, started_at, finished_at = _run_training_process(
        db=db,
        task_id=task_id,
        script_path=script_path,
        input_csv=input_csv,
        run_dir=run_dir,
        logs_path=logs_path,
    )
    if return_code != 0:
        model.status = "untrained"
        db.add(model)
        db.commit()
        tail = logs_path.read_text(encoding="utf-8", errors="replace")[-1000:]
        missing_module = None
        for line in reversed(tail.splitlines()):
            if "ModuleNotFoundError: No module named" in line:
                missing_module = line.split("No module named", 1)[-1].strip().strip("'\"")
                break
        if missing_module:
            raise RuntimeError(
                f"Training failed because the backend Python environment is missing dependency "
                f"'{missing_module}'. Install backend requirements and retry. {tail}"
            )
        raise RuntimeError(f"Training failed with code {return_code}. {tail}")

    metrics = _parse_metrics(run_dir / "results.json")
    checkpoint_path = run_dir / "checkpoint.zip"
    manifest = {
        "model_id": model.id,
        "model_name": model.name,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "created_at": finished_at.isoformat(),
        "entry_script": str(script_path),
        "command": command,
        "record_count": record_count,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "metrics": metrics,
        "prediction_format": "predictions_test_full.csv / predictions_week0.csv",
    }
    _create_checkpoint_zip(run_dir, checkpoint_path, manifest)

    latest_path = model_dir / "checkpoint.zip"
    shutil.copyfile(checkpoint_path, latest_path)

    model.status = "trained"
    model.trained_at = finished_at
    db.add(model)
    db.commit()
    db.refresh(model)

    _log(db, task_id, "info", f"Training completed. Checkpoint: {checkpoint_path}")
    return {
        "model_id": model.id,
        "model_name": model.name,
        "dataset_id": dataset.id,
        "run_dir": str(run_dir),
        "checkpoint_path": str(checkpoint_path),
        "download_path": str(latest_path),
        "metrics": metrics,
    }
