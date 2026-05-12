from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.dataset_record import DatasetRecord
from app.models.base_price_data import BasePriceData
from app.models.prediction_run_record import PredictionRunRecord
from app.services.prediction_service import get_base_model_prediction


@dataclass
class RunMetrics:
    mae: float
    rmse: float
    r2: float
    imape: float
    score: float


def _safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _compute_imape(actual: float, predicted: float) -> float:
    actual_floor = max(abs(actual), 150.0)
    predicted_floor = max(abs(predicted), 150.0)
    denominator = max(actual_floor, predicted_floor)
    if denominator <= 0:
        return 0.0
    ape = abs(actual - predicted) / denominator
    return min(ape, 1.0)


def compute_metrics(actuals: list[float], preds: list[float]) -> RunMetrics:
    if not actuals or len(actuals) != len(preds):
        return RunMetrics(mae=0.0, rmse=0.0, r2=0.0, imape=0.0, score=0.0)

    errors = [p - a for a, p in zip(actuals, preds)]
    abs_errors = [abs(e) for e in errors]
    sq_errors = [e * e for e in errors]
    imapes = [_compute_imape(a, p) for a, p in zip(actuals, preds)]

    mae = _safe_mean(abs_errors)
    rmse = sqrt(_safe_mean(sq_errors))
    imape = _safe_mean(imapes)
    # 评分 = 100 * (1 - MAPE)
    score = max(0.0, min(100.0, (1.0 - imape) * 100.0))

    mean_actual = _safe_mean(actuals)
    ss_res = sum((p - a) ** 2 for a, p in zip(actuals, preds))
    ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
    r2 = 0.0 if ss_tot <= 1e-12 else 1 - (ss_res / ss_tot)

    return RunMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        r2=round(r2, 4),
        imape=round(imape, 6),
        score=round(score, 6),
    )


def build_run_records(
    db: Session,
    *,
    dataset_id: int,
    prediction_type: str,
    start_time: datetime,
    end_time: datetime,
) -> tuple[list[PredictionRunRecord], RunMetrics]:
    rows = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id,
        DatasetRecord.record_time >= start_time,
        DatasetRecord.record_time <= end_time,
    ).order_by(DatasetRecord.record_time.asc()).all()
    if not rows:
        rows = db.query(BasePriceData).filter(
            BasePriceData.record_time >= start_time,
            BasePriceData.record_time <= end_time,
        ).order_by(BasePriceData.record_time.asc()).all()

    records: list[PredictionRunRecord] = []
    actuals: list[float] = []
    preds: list[float] = []

    for row in rows:
        actual = float(row.price_kwh)
        predicted = get_base_model_prediction(db, dataset_id, row.record_time, prediction_type)
        if predicted is None:
            continue
        records.append(
            PredictionRunRecord(
                record_time=row.record_time,
                actual_price=actual,
                predicted_price=float(predicted),
            )
        )
        actuals.append(actual)
        preds.append(float(predicted))

    metrics = compute_metrics(actuals, preds)
    return records, metrics


def build_input_csv(
    db: Session,
    *,
    dataset_id: int,
    start_time: datetime,
    end_time: datetime,
    output_path: str,
) -> int:
    rows = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id,
        DatasetRecord.record_time >= start_time,
        DatasetRecord.record_time <= end_time,
    ).order_by(DatasetRecord.record_time.asc()).all()
    if not rows:
        rows = db.query(BasePriceData).filter(
            BasePriceData.record_time >= start_time,
            BasePriceData.record_time <= end_time,
        ).order_by(BasePriceData.record_time.asc()).all()

    import csv

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["record_time", "actual_price", "load_kw"])
        for row in rows:
            writer.writerow(
                [
                    row.record_time.isoformat(),
                    float(row.price_kwh),
                    float(getattr(row, "load_kw", 0.0) or 0.0),
                ]
            )
    return len(rows)


def build_records_from_output_csv(
    db: Session,
    *,
    dataset_id: int,
    output_csv: str,
) -> tuple[list[PredictionRunRecord], RunMetrics]:
    import csv
    from datetime import datetime

    actual_map = {}
    rows = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).all()
    if not rows:
        rows = db.query(BasePriceData).all()
    for row in rows:
        iso = row.record_time.isoformat()
        actual_map[iso] = float(row.price_kwh)
        actual_map[iso.replace("T", " ")] = float(row.price_kwh)

    records: list[PredictionRunRecord] = []
    actuals: list[float] = []
    preds: list[float] = []

    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record_time = row.get("record_time") or row.get("date")
            if not record_time:
                continue
            actual = actual_map.get(record_time)
            if actual is None:
                continue
            predicted = row.get("predicted_price") or row.get("y_test_pred") or row.get("pred")
            if predicted is None:
                continue
            try:
                pred_val = float(predicted)
            except ValueError:
                continue

            try:
                dt = datetime.fromisoformat(record_time)
            except ValueError:
                dt = datetime.strptime(record_time, "%Y-%m-%d %H:%M:%S")

            records.append(
                PredictionRunRecord(
                    record_time=dt,
                    actual_price=actual,
                    predicted_price=pred_val,
                )
            )
            actuals.append(actual)
            preds.append(pred_val)

    metrics = compute_metrics(actuals, preds)
    return records, metrics
