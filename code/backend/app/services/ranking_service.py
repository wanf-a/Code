from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from math import sqrt
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.dataset_record import DatasetRecord
from app.models.plan import Plan
from app.models.prediction_detail import PredictionDetail
from app.models.base_prediction_data import BasePredictionData
from app.models.prediction_run import PredictionRun
from app.models.base_price_data import BasePriceData
from app.services.inference_service import has_model_weights, run_inference


def _build_epf_summaries(
    db: Session,
    *,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    model_name: Optional[str],
) -> list[Dict[str, object]]:
    if not start_time or not end_time:
        return []

    from app.models.dataset import Dataset
    from app.models.model import Model as ModelEntity

    models = db.query(ModelEntity).all()
    if not models:
        return []

    summaries: list[Dict[str, object]] = []
    for model_entity in models:
        name = model_entity.name
        if model_name and model_name.lower() not in name.lower():
            continue
        if not has_model_weights(name):
            continue

        dataset_id = model_entity.dataset_id
        if not dataset_id:
            ds = db.query(Dataset).first()
            dataset_id = ds.id if ds else None
        if not dataset_id:
            continue

        try:
            rows = run_inference(
                db=db,
                model_name=name,
                dataset_id=dataset_id,
                start_time=start_time,
                end_time=end_time,
            )
        except (ValueError, Exception):
            continue

        if not rows:
            continue

        actuals = [r["real"] for r in rows]
        preds = [r["qr_50"] for r in rows]
        errors = [p - a for a, p in zip(actuals, preds)]
        abs_errors = [abs(e) for e in errors]
        sq_errors = [e * e for e in errors]
        imape_values = [_compute_imape(a, p) for a, p in zip(actuals, preds)]

        mae = _safe_mean(abs_errors)
        rmse = sqrt(_safe_mean(sq_errors))
        imape = _safe_mean(imape_values)
        score = max(0.0, min(100.0, (1.0 - imape) * 100.0))

        mean_actual = _safe_mean(actuals)
        ss_res = sum((p - a) ** 2 for a, p in zip(actuals, preds))
        ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
        r2 = 0.0 if ss_tot <= 1e-12 else 1 - (ss_res / ss_tot)

        period_start = rows[0]["record_time"]
        period_end = rows[-1]["record_time"]

        dataset_name = "广东电价数据"
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if ds:
            dataset_name = ds.name

        load_label = "未知"
        wind_label = "未知"
        weather_label = "未知"
        base_rows = db.query(
            BasePriceData.load_kw,
            BasePriceData.wind_speed,
            BasePriceData.cloud_cover,
        ).filter(
            BasePriceData.record_time >= period_start,
            BasePriceData.record_time <= period_end,
        ).all()
        if base_rows:
            avg_load = _safe_mean(_to_float(item.load_kw, 0.0) for item in base_rows)
            avg_wind = _safe_mean(_to_float(item.wind_speed, -1.0) for item in base_rows)
            avg_cloud = _safe_mean(_to_float(item.cloud_cover, 0.0) for item in base_rows)
            load_label = _load_label(avg_load)
            wind_label = _wind_label(avg_wind)
            weather_label = _weather_label_from_cloud(avg_cloud)

        summaries.append(
            {
                "plan_id": model_entity.id,
                "dataset": dataset_name,
                "type": "周前概率",
                "model": name,
                "period": _period_text(period_start, period_end),
                "load": load_label,
                "wind": wind_label,
                "weather_type": weather_label,
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "r2": round(r2, 4),
                "imape": round(imape, 6),
                "score": round(score, 6),
                "sample_count": len(rows),
            }
        )
    return summaries


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


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


def _load_label(avg_load: float) -> str:
    if avg_load <= 0:
        return "未知"
    if avg_load < 50000:
        return "低负荷"
    if avg_load < 70000:
        return "中负荷"
    return "高负荷"


def _wind_label(avg_wind: float) -> str:
    if avg_wind < 0:
        return "未知"
    if avg_wind < 3:
        return "微风"
    if avg_wind < 6:
        return "和风"
    if avg_wind < 10:
        return "大风"
    return "强风"


def _normalize_weather_text(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "未知"
    if text in {"unknown", "unk", "na", "none", "null"}:
        return "未知"
    if "晴" in text:
        return "晴天"
    if "雨" in text:
        return "雨天"
    if "阴" in text:
        return "阴天"
    if "云" in text:
        return "多云"
    return value


def _weather_label_from_cloud(cloud_cover: float) -> str:
    if cloud_cover <= 30:
        return "晴天"
    if cloud_cover >= 70:
        return "阴天"
    return "多云"


def _weather_label(weather_types: Iterable[str]) -> str:
    cleaned = [w.strip() for w in weather_types if w and w.strip()]
    if not cleaned:
        return "未知"
    winner = Counter(cleaned).most_common(1)[0][0]
    return _normalize_weather_text(winner)


def _period_text(start_time: datetime, end_time: datetime) -> str:
    return f"{start_time.date()}-{end_time.date()}"


def _type_label(plan_type: Optional[str]) -> str:
    raw = (plan_type or "").strip().lower()
    if "week" in raw or "周" in raw:
        return "周前概率"
    return "周前概率"


def calculate_ranking_summary(
    db: Session,
    *,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    model_name: Optional[str] = None,
    rank_type: Optional[str] = None,
    source: Optional[str] = None,
) -> list[Dict[str, object]]:
    # Prefer latest prediction_run if available; otherwise fallback to prediction_detail.
    if source == "epf":
        return _build_epf_summaries(
            db,
            start_time=start_time,
            end_time=end_time,
            model_name=model_name,
        )

    run_query = (
        db.query(
            PredictionRun.id.label("run_id"),
            PredictionRun.plan_id,
            PredictionRun.start_time,
            PredictionRun.end_time,
            PredictionRun.mae,
            PredictionRun.rmse,
            PredictionRun.r2,
            PredictionRun.imape,
            PredictionRun.score,
            PredictionRun.record_count,
            Plan.name.label("plan_name"),
            Plan.plan_type.label("plan_type"),
            Plan.dataset_id.label("dataset_id"),
        )
        .join(Plan, PredictionRun.plan_id == Plan.id)
        .filter(PredictionRun.status == "completed")
        .order_by(PredictionRun.created_at.desc())
    )
    if model_name:
        run_query = run_query.filter(Plan.name.contains(model_name))
    if rank_type:
        run_query = run_query.filter(Plan.plan_type.contains(rank_type))
    runs = run_query.all()

    if runs:
        summaries: list[Dict[str, object]] = []
        seen_plans: set[int] = set()
        for run in runs:
            if run.plan_id in seen_plans:
                continue
            seen_plans.add(run.plan_id)
            row_start = run.start_time
            row_end = run.end_time
            if start_time and row_end and row_end < start_time:
                continue
            if end_time and row_start and row_start > end_time:
                continue

            dataset_id = run.dataset_id
            dataset_name = "广东电价数据"
            if dataset_id is not None:
                from app.models.dataset import Dataset

                ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                if ds:
                    dataset_name = ds.name

            load_label = "未知"
            wind_label = "未知"
            weather_label = "未知"
            if dataset_id is not None and row_start and row_end:
                label_query = db.query(
                    DatasetRecord.load_kw,
                    DatasetRecord.wind_speed,
                    DatasetRecord.weather_type,
                ).filter(
                    DatasetRecord.dataset_id == dataset_id,
                    DatasetRecord.record_time >= row_start,
                    DatasetRecord.record_time <= row_end,
                )
                if start_time:
                    label_query = label_query.filter(DatasetRecord.record_time >= start_time)
                if end_time:
                    label_query = label_query.filter(DatasetRecord.record_time <= end_time)
                label_rows = label_query.all()
                if label_rows:
                    avg_load = _safe_mean(_to_float(item.load_kw, 0.0) for item in label_rows)
                    avg_wind = _safe_mean(_to_float(item.wind_speed, -1.0) for item in label_rows)
                    load_label = _load_label(avg_load)
                    wind_label = _wind_label(avg_wind)
                    weather_label = _weather_label(item.weather_type for item in label_rows)

                if wind_label == "未知" or weather_label == "未知":
                    base_query = db.query(
                        BasePriceData.wind_speed,
                        BasePriceData.cloud_cover,
                    ).filter(
                        BasePriceData.record_time >= row_start,
                        BasePriceData.record_time <= row_end,
                    )
                    if start_time:
                        base_query = base_query.filter(BasePriceData.record_time >= start_time)
                    if end_time:
                        base_query = base_query.filter(BasePriceData.record_time <= end_time)
                    base_rows = base_query.all()
                    if base_rows:
                        if wind_label == "未知":
                            avg_base_wind = _safe_mean(
                                _to_float(item.wind_speed, -1.0) for item in base_rows
                            )
                            wind_label = _wind_label(avg_base_wind)
                        if weather_label == "未知":
                            avg_cloud = _safe_mean(
                                _to_float(item.cloud_cover, 0.0) for item in base_rows
                            )
                            weather_label = _weather_label_from_cloud(avg_cloud)

            summaries.append(
                {
                    "plan_id": run.plan_id,
                    "dataset": dataset_name,
                    "type": _type_label(run.plan_type),
                    "model": run.plan_name,
                    "period": _period_text(row_start, row_end),
                    "load": load_label,
                    "wind": wind_label,
                    "weather_type": weather_label,
                    "mae": float(run.mae or 0.0),
                    "rmse": float(run.rmse or 0.0),
                    "r2": float(run.r2 or 0.0),
                    "imape": float(run.imape or 0.0),
                    "score": float(run.score or 0.0),
                    "sample_count": int(run.record_count or 0),
                }
            )

        summaries.sort(key=lambda item: (item["score"], -item["imape"], -item["sample_count"]), reverse=True)
        return summaries

    # EPF fallback: return fixed 4-model summaries when no prediction_run data.
    summaries = _build_epf_summaries(
        db,
        start_time=start_time,
        end_time=end_time,
        model_name=model_name,
    )
    if summaries:
        return summaries

    query = (
        db.query(
            PredictionDetail.plan_id,
            PredictionDetail.record_time,
            PredictionDetail.actual_price,
            PredictionDetail.predicted_price,
            Plan.name.label("plan_name"),
            Plan.plan_type.label("plan_type"),
            Plan.dataset_id.label("dataset_id"),
        )
        .join(Plan, PredictionDetail.plan_id == Plan.id)
    )
    if start_time:
        query = query.filter(PredictionDetail.record_time >= start_time)
    if end_time:
        query = query.filter(PredictionDetail.record_time <= end_time)
    if model_name:
        query = query.filter(Plan.name.contains(model_name))
    if rank_type:
        query = query.filter(Plan.plan_type.contains(rank_type))

    rows = query.order_by(PredictionDetail.record_time.asc()).all()
    grouped: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "plan_name": "",
            "plan_type": "",
            "dataset_id": None,
            "records": [],
            "start_time": None,
            "end_time": None,
        }
    )
    for row in rows:
        pack = grouped[row.plan_id]
        pack["plan_name"] = row.plan_name or ""
        pack["plan_type"] = row.plan_type or ""
        pack["dataset_id"] = row.dataset_id
        pack["records"].append(
            (_to_float(row.actual_price), _to_float(row.predicted_price), row.record_time)
        )
        if pack["start_time"] is None or row.record_time < pack["start_time"]:
            pack["start_time"] = row.record_time
        if pack["end_time"] is None or row.record_time > pack["end_time"]:
            pack["end_time"] = row.record_time

    if not grouped:
        return []

    dataset_ids = [info["dataset_id"] for info in grouped.values() if info["dataset_id"] is not None]
    dataset_name_map: dict[int, str] = {}
    if dataset_ids:
        from app.models.dataset import Dataset

        dataset_rows = db.query(Dataset.id, Dataset.name).filter(Dataset.id.in_(dataset_ids)).all()
        dataset_name_map = {item.id: item.name for item in dataset_rows}

    summaries: list[Dict[str, object]] = []
    for plan_id, info in grouped.items():
        records = info["records"]
        if not records:
            continue

        row_start = info["start_time"]
        row_end = info["end_time"]
        # Uploaded CSV may write predicted_price == actual_price as placeholder.
        # In that case, fallback to base_prediction_data for realistic scoring.
        same_point_count = sum(1 for actual, pred, _ in records if abs(actual - pred) <= 1e-9)
        if (
            row_start is not None
            and row_end is not None
            and same_point_count == len(records)
        ):
            base_query = db.query(
                BasePredictionData.actual_price,
                BasePredictionData.predicted_price,
            ).filter(
                BasePredictionData.record_time >= row_start,
                BasePredictionData.record_time <= row_end,
            )
            if start_time:
                base_query = base_query.filter(BasePredictionData.record_time >= start_time)
            if end_time:
                base_query = base_query.filter(BasePredictionData.record_time <= end_time)
            base_rows = base_query.all()
            if base_rows:
                records = [
                    (_to_float(item.actual_price), _to_float(item.predicted_price), row_start)
                    for item in base_rows
                ]

        actuals = [r[0] for r in records]
        preds = [r[1] for r in records]
        errors = [pred - actual for actual, pred in zip(actuals, preds)]
        abs_errors = [abs(err) for err in errors]
        sq_errors = [err * err for err in errors]
        imape_values = [_compute_imape(actual, pred) for actual, pred in zip(actuals, preds)]

        mae = _safe_mean(abs_errors)
        rmse = sqrt(_safe_mean(sq_errors))
        imape = _safe_mean(imape_values)
        # 评分 = 100 * (1 - MAPE)
        score = max(0.0, min(100.0, (1.0 - imape) * 100.0))

        mean_actual = _safe_mean(actuals)
        ss_res = sum((pred - actual) ** 2 for actual, pred in zip(actuals, preds))
        ss_tot = sum((actual - mean_actual) ** 2 for actual in actuals)
        r2 = 0.0 if ss_tot <= 1e-12 else 1 - (ss_res / ss_tot)

        dataset_id = info["dataset_id"]
        dataset_name = dataset_name_map.get(dataset_id, "广东电价数据")
        load_label = "未知"
        wind_label = "未知"
        weather_label = "未知"
        if dataset_id is not None and row_start and row_end:
            label_query = db.query(
                DatasetRecord.load_kw,
                DatasetRecord.wind_speed,
                DatasetRecord.weather_type,
            ).filter(
                DatasetRecord.dataset_id == dataset_id,
                DatasetRecord.record_time >= row_start,
                DatasetRecord.record_time <= row_end,
            )
            if start_time:
                label_query = label_query.filter(DatasetRecord.record_time >= start_time)
            if end_time:
                label_query = label_query.filter(DatasetRecord.record_time <= end_time)
            label_rows = label_query.all()
            if label_rows:
                avg_load = _safe_mean(_to_float(item.load_kw, 0.0) for item in label_rows)
                avg_wind = _safe_mean(_to_float(item.wind_speed, -1.0) for item in label_rows)
                load_label = _load_label(avg_load)
                wind_label = _wind_label(avg_wind)
                weather_label = _weather_label(item.weather_type for item in label_rows)

                # Fallback to base_price_data if dataset records miss wind/weather.
                if wind_label == "未知" or weather_label == "未知":
                    base_query = db.query(
                        BasePriceData.wind_speed,
                        BasePriceData.cloud_cover,
                    ).filter(
                        BasePriceData.record_time >= row_start,
                        BasePriceData.record_time <= row_end,
                    )
                    if start_time:
                        base_query = base_query.filter(BasePriceData.record_time >= start_time)
                    if end_time:
                        base_query = base_query.filter(BasePriceData.record_time <= end_time)
                    base_rows = base_query.all()
                    if base_rows:
                        if wind_label == "未知":
                            avg_base_wind = _safe_mean(
                                _to_float(item.wind_speed, -1.0) for item in base_rows
                            )
                            wind_label = _wind_label(avg_base_wind)
                        if weather_label == "未知":
                            avg_cloud = _safe_mean(
                                _to_float(item.cloud_cover, 0.0) for item in base_rows
                            )
                            weather_label = _weather_label_from_cloud(avg_cloud)

        summaries.append(
            {
                "plan_id": plan_id,
                "dataset": dataset_name,
                "type": _type_label(info["plan_type"]),
                "model": info["plan_name"],
                "period": _period_text(row_start, row_end),
                "load": load_label,
                "wind": wind_label,
                "weather_type": weather_label,
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "r2": round(r2, 4),
                "imape": round(imape, 6),
                "score": round(score, 6),
                "sample_count": len(records),
            }
        )

    summaries.sort(key=lambda item: (item["score"], -item["imape"], -item["sample_count"]), reverse=True)
    return summaries
