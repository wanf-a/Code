from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import models as models_route
from app.core.config import get_settings
from app.models.dataset import Dataset
from app.models.dataset_record import DatasetRecord
from app.models.task import Task
from app.services.task_service import execute_task


def _create_dataset_with_records(db: Session, admin_id: int) -> Dataset:
    dataset = Dataset(
        name="Training Dataset",
        description="Dataset for model training API test",
        created_by=admin_id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    for day in range(1, 4):
        for hour in range(2):
            db.add(
                DatasetRecord(
                    dataset_id=dataset.id,
                    record_time=datetime(2024, 1, day, hour, 0, 0),
                    price_kwh=0.52 + day + hour,
                    generation_kwh=0,
                    load_kw=100 + day * 10 + hour,
                    weather_type="晴",
                    temperature=25 + day,
                    wind_speed=2 + hour,
                    cloud_cover=10 + day,
                    is_holiday=0,
                )
            )
    db.commit()
    db.refresh(dataset)
    return dataset


def test_train_model_runs_and_generates_checkpoint(
    client: TestClient,
    db: Session,
    admin_user,
    auth_headers: dict,
    temp_upload_dir: str,
    monkeypatch,
):
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = temp_upload_dir

    try:
        def fake_execute_task_background(task_id: int) -> None:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                execute_task(db, task)

        monkeypatch.setattr(models_route, "_execute_task_background", fake_execute_task_background)

        dataset = _create_dataset_with_records(db, admin_user.id)
        model_script = b"""
import json
import os
import sys

def main():
    data_path = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)
    with open(data_path, "r", encoding="gb18030") as f:
        line_count = sum(1 for _ in f)
    with open(os.path.join(output_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": line_count - 1}, f)
    with open(os.path.join(output_dir, "predictions_test_full.csv"), "w", encoding="utf-8") as f:
        f.write("time,prediction\\n2024-01-01 00:00,1\\n")
    with open(os.path.join(output_dir, "predictions_week0.csv"), "w", encoding="utf-8") as f:
        f.write("time,prediction\\n2024-01-01 00:00,1\\n")

if __name__ == "__main__":
    main()
"""

        upload_response = client.post(
            "/api/v1/models/upload",
            headers=auth_headers,
            files={"file": ("toy_model.py", BytesIO(model_script), "text/x-python")},
            data={
                "name": "Toy Train Model",
                "description": "toy",
                "dataset_id": str(dataset.id),
                "train_start_date": "2024-01-01",
                "train_end_date": "2024-01-03",
                "prediction_type": "week_ahead",
            },
        )
        assert upload_response.status_code == 200, upload_response.text
        model_id = upload_response.json()["id"]

        train_response = client.post(f"/api/v1/models/{model_id}/train", headers=auth_headers)
        assert train_response.status_code == 200, train_response.text
        task_id = train_response.json()["task_id"]

        task = db.query(Task).filter(Task.id == task_id).first()
        assert task is not None
        db.refresh(task)
        assert task.status == "completed"
        assert task.result_json

        result = json.loads(task.result_json)
        checkpoint_path = Path(result["checkpoint_path"])
        download_path = Path(result["download_path"])
        run_dir = Path(result["run_dir"])

        assert checkpoint_path.exists()
        assert download_path.exists()
        assert run_dir.joinpath("results.json").exists()
        assert run_dir.joinpath("predictions_test_full.csv").exists()
        assert run_dir.joinpath("predictions_week0.csv").exists()

        model_detail = client.get(f"/api/v1/models/{model_id}", headers=auth_headers)
        assert model_detail.status_code == 200
        assert model_detail.json()["status"] == "trained"
        assert model_detail.json()["trained_at"] is not None
    finally:
        settings.upload_dir = old_upload_dir
