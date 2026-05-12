from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.dataset_record import DatasetRecord
from app.models.model import Model as ModelEntity
from app.models.plan import Plan
from app.models.prediction_run import PredictionRun
from app.models.prediction_run_record import PredictionRunRecord
from app.models.run_artifact import RunArtifact
from app.services.model_runner import run_model_file
from app.services.prediction_run_service import (
    build_input_csv,
    build_records_from_output_csv,
    build_run_records,
)
from app.services.version_service import get_or_create_dataset_version, get_or_create_model_version


def execute_prediction_run(
    db: Session,
    *,
    plan_id: int,
    model_id: Optional[int],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    settings: Settings,
) -> PredictionRun:
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise ValueError("Plan not found")
    if not plan.dataset_id:
        raise ValueError("Plan has no dataset assigned")
    if model_id is None and plan.model_id:
        model_id = plan.model_id

    if start_time is None or end_time is None:
        min_t, max_t = db.query(
            func.min(DatasetRecord.record_time),
            func.max(DatasetRecord.record_time),
        ).filter(DatasetRecord.dataset_id == plan.dataset_id).one()
        if min_t is None or max_t is None:
            raise ValueError("Dataset has no records")
        start_time = start_time or min_t
        end_time = end_time or max_t

    if start_time > end_time:
        raise ValueError("start_time cannot be greater than end_time")

    run = PredictionRun(
        plan_id=plan.id,
        model_id=model_id,
        status="running",
        start_time=start_time,
        end_time=end_time,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    input_root = settings.input_root
    output_root = settings.output_root
    case_id = settings.case_id
    case_time = settings.case_time

    run_dir = Path(output_root) / f"run_{run.id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(input_root) / f"run_{run.id}_input.csv"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "output.csv"

    build_input_csv(
        db,
        dataset_id=plan.dataset_id,
        start_time=start_time,
        end_time=end_time,
        output_path=str(input_path),
    )

    model_version = get_or_create_model_version(db, model_id)
    dataset_version = get_or_create_dataset_version(db, plan.dataset_id)

    records: list[PredictionRunRecord] = []
    metrics = None

    if model_id:
        m = db.query(ModelEntity).filter(ModelEntity.id == model_id).first()
        model_file = m.file_path if m else None
        if model_file:
            ok, msg = run_model_file(model_file, str(input_path), str(output_path))
            if ok:
                records, metrics = build_records_from_output_csv(
                    db,
                    dataset_id=plan.dataset_id,
                    output_csv=str(output_path),
                )
            else:
                run.message = msg
        else:
            run.message = "Model file not found, fallback to base prediction."

    if not records or metrics is None:
        records, metrics = build_run_records(
            db,
            dataset_id=plan.dataset_id,
            prediction_type="week_ahead",
            start_time=start_time,
            end_time=end_time,
        )

    if not records:
        run.status = "failed"
        run.message = run.message or "No valid prediction records in the selected range."
        run.finished_at = datetime.utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    for record in records:
        record.run_id = run.id
    db.add_all(records)
    db.commit()

    run.status = "completed"
    run.record_count = len(records)
    run.mae = metrics.mae
    run.rmse = metrics.rmse
    run.r2 = metrics.r2
    run.imape = metrics.imape
    run.score = metrics.score
    run.finished_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)

    artifact = RunArtifact(
        run_id=run.id,
        model_version_id=model_version.id,
        dataset_version_id=dataset_version.id,
        case_id=case_id,
        case_time=case_time,
        input_root=input_root,
        output_root=output_root,
        input_path=str(input_path),
        output_path=str(output_path) if output_path.exists() else None,
    )
    db.add(artifact)
    db.commit()
    return run
