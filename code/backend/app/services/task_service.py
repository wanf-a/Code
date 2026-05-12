from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.task import Task
from app.models.task_log import TaskLog
from app.services.run_executor import execute_prediction_run
from app.services.training_service import train_uploaded_model


def _log(db: Session, task_id: int, level: str, message: str) -> None:
    entry = TaskLog(task_id=task_id, level=level, message=message)
    db.add(entry)
    db.commit()


def execute_task(db: Session, task: Task) -> Task:
    task.status = "running"
    task.started_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)

    payload: dict[str, Any] = {}
    try:
        payload = json.loads(task.payload_json or "{}")
    except json.JSONDecodeError:
        task.status = "failed"
        task.last_error = "Invalid payload JSON"
        task.finished_at = datetime.utcnow()
        db.add(task)
        db.commit()
        return task

    try:
        if task.task_type == "model_train":
            result = train_uploaded_model(
                db,
                model_id=int(payload.get("model_id")),
                task_id=task.id,
                settings=get_settings(),
            )
            task.result_json = json.dumps(result, ensure_ascii=False)
            task.status = "completed"
        elif task.task_type == "prediction_run":
            def _parse_dt(value: Any) -> Any:
                if value is None:
                    return None
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value)
                    except ValueError:
                        return None
                return None

            run = execute_prediction_run(
                db,
                plan_id=int(payload.get("plan_id")),
                model_id=payload.get("model_id"),
                start_time=_parse_dt(payload.get("start_time")),
                end_time=_parse_dt(payload.get("end_time")),
                settings=get_settings(),
            )
            task.result_json = json.dumps({"run_id": run.id}, ensure_ascii=False)
            if run.status == "completed":
                task.status = "completed"
            else:
                task.status = "failed"
                task.last_error = run.message or "Prediction run failed"
        else:
            task.status = "failed"
            task.last_error = f"Unsupported task type: {task.task_type}"
    except Exception as exc:
        task.status = "failed"
        task.last_error = str(exc)[:200]
        _log(db, task.id, "error", str(exc))

    task.finished_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
