"""Import base datasets into database.

This module supports both legacy CSV format and EPF-generated CSV format.
"""
from __future__ import annotations

import csv
import os
from glob import glob
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.base_prediction_data import BasePredictionData
from app.models.base_price_data import BasePriceData
from app.models.tcn_prediction import TcnProbPrediction


def parse_datetime(date_str: str) -> datetime:
    formats = (
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y-%m-%d",
    )
    value = (date_str or "").strip()
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse datetime: {date_str}")


def read_csv_file(csv_path: str) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"):
        try:
            with open(csv_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode file: {csv_path}")


def _safe_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _normalize_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "")


def _find_column_by_names(header: Iterable[str], candidates: Iterable[str]) -> Optional[int]:
    normalized_header = [_normalize_header(h) for h in header]
    normalized_candidates = {_normalize_header(c) for c in candidates}
    for idx, col in enumerate(normalized_header):
        if col in normalized_candidates:
            return idx
    return None


def _find_column_contains(header: Iterable[str], tokens: Iterable[str]) -> Optional[int]:
    normalized_header = [_normalize_header(h) for h in header]
    normalized_tokens = [_normalize_header(t) for t in tokens]
    for idx, col in enumerate(normalized_header):
        if any(token in col for token in normalized_tokens):
            return idx
    return None


def _latest_glob(pattern: str) -> Optional[str]:
    matches = [Path(p) for p in glob(pattern)]
    if not matches:
        return None
    latest = max(matches, key=lambda p: p.stat().st_mtime)
    return str(latest)


def _first_existing(paths: Iterable[str]) -> Optional[str]:
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def import_base_price_data(db: Session, csv_path: str | None) -> int:
    existing_count = db.query(BasePriceData).count()
    if existing_count > 0:
        print(f"[SKIP] base_price_data already exists ({existing_count})")
        return existing_count

    if not csv_path or not os.path.exists(csv_path):
        print(f"[WARN] Base price CSV does not exist: {csv_path}")
        return 0

    try:
        content = read_csv_file(csv_path)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 0

    rows = list(csv.reader(StringIO(content)))
    if len(rows) < 2:
        print("[WARN] Base price CSV has no data rows")
        return 0

    count = 0
    batch_size = 1000
    for row in rows[1:]:
        if len(row) < 6:
            continue
        try:
            record = BasePriceData(
                record_time=parse_datetime(row[0]),
                price_kwh=_safe_float(row[1]),
                load_kw=_safe_float(row[2]),
                temperature=_safe_float(row[3], default=None),  # type: ignore[arg-type]
                wind_speed=_safe_float(row[4], default=None),   # type: ignore[arg-type]
                cloud_cover=_safe_float(row[5], default=None),  # type: ignore[arg-type]
            )
            db.add(record)
            count += 1
            if count % batch_size == 0:
                db.commit()
        except Exception as e:
            print(f"[WARN] Failed to parse row in base price CSV: {row}, err={e}")
            continue

    db.commit()
    print(f"[OK] Imported base_price_data: {count}")
    return count


def _select_prediction_indices(header: list[str]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    time_idx = _find_column_by_names(header, ("date", "time", "record_time", "时间"))
    if time_idx is None:
        time_idx = _find_column_contains(header, ("date", "time", "时间"))

    actual_idx = _find_column_by_names(header, ("y_test_true", "true", "actual", "real"))
    if actual_idx is None:
        actual_idx = _find_column_contains(header, ("y_test_true", "true", "actual", "real"))

    pred_priority = (
        "y_test_pred",
        "predicted_price",
        "predicted",
        "prediction",
        "ensemble_q0.5",
        "tcn_q0.5",
        "mamba_q0.5",
        "nlinear_q0.5",
    )
    pred_idx = _find_column_by_names(header, pred_priority)
    if pred_idx is None:
        pred_idx = _find_column_contains(header, ("q0.5", "q0_5", "median"))
    if pred_idx is None:
        # fallback to generic "pred*" columns
        for idx, col in enumerate([_normalize_header(h) for h in header]):
            if "pred" in col and "true" not in col:
                pred_idx = idx
                break

    return time_idx, actual_idx, pred_idx


def import_base_prediction_data(db: Session, csv_path: str | None) -> int:
    existing_count = db.query(BasePredictionData).count()
    if existing_count > 0:
        print(f"[SKIP] base_prediction_data already exists ({existing_count})")
        return existing_count

    if not csv_path or not os.path.exists(csv_path):
        print(f"[WARN] Base prediction CSV does not exist: {csv_path}")
        return 0

    try:
        content = read_csv_file(csv_path)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 0

    rows = list(csv.reader(StringIO(content)))
    if len(rows) < 2:
        print("[WARN] Base prediction CSV has no data rows")
        return 0

    header = [str(h).strip() for h in rows[0]]
    time_idx, actual_idx, pred_idx = _select_prediction_indices(header)

    # Legacy fallback: first 3 columns are date, true, pred.
    if time_idx is None or actual_idx is None or pred_idx is None:
        if len(header) >= 3:
            time_idx, actual_idx, pred_idx = 0, 1, 2
        else:
            print(f"[WARN] Cannot detect columns for base prediction CSV: {header}")
            return 0

    count = 0
    batch_size = 1000
    required_max = max(time_idx, actual_idx, pred_idx)
    for row in rows[1:]:
        if len(row) <= required_max:
            continue
        try:
            record = BasePredictionData(
                record_time=parse_datetime(row[time_idx]),
                actual_price=_safe_float(row[actual_idx]),
                predicted_price=_safe_float(row[pred_idx]),
            )
            db.add(record)
            count += 1
            if count % batch_size == 0:
                db.commit()
        except Exception as e:
            print(f"[WARN] Failed to parse row in base prediction CSV: {row}, err={e}")
            continue

    db.commit()
    print(f"[OK] Imported base_prediction_data: {count}")
    return count


def _select_tcn_indices(header: list[str]) -> Optional[Dict[str, int]]:
    real_idx = _find_column_by_names(header, ("real", "true", "actual"))
    time_idx = _find_column_by_names(header, ("time", "date", "record_time"))

    quantile_map = {
        "qr_005": ("qr-0.005", "qr_0.005", "tcn_q0.005"),
        "qr_025": ("qr-0.025", "qr_0.025", "tcn_q0.025"),
        "qr_05": ("qr-0.05", "qr_0.05", "tcn_q0.05"),
        "qr_50": ("qr-0.5", "qr_0.5", "tcn_q0.5"),
        "qr_95": ("qr-0.95", "qr_0.95", "tcn_q0.95"),
        "qr_975": ("qr-0.975", "qr_0.975", "tcn_q0.975"),
        "qr_995": ("qr-0.995", "qr_0.995", "tcn_q0.995"),
    }

    indices: Dict[str, int] = {}
    if real_idx is None:
        return None
    indices["real"] = real_idx
    if time_idx is not None:
        indices["time"] = time_idx

    for field, candidates in quantile_map.items():
        idx = _find_column_by_names(header, candidates)
        if idx is None:
            return None
        indices[field] = idx

    return indices


def import_tcn_prob_data(db: Session, csv_path: str | None) -> int:
    existing_count = db.query(TcnProbPrediction).count()
    if existing_count > 0:
        print(f"[SKIP] tcn_prob_prediction already exists ({existing_count})")
        return existing_count

    if not csv_path or not os.path.exists(csv_path):
        print(f"[WARN] TCN probability CSV does not exist: {csv_path}")
        return 0

    try:
        content = read_csv_file(csv_path)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 0

    reader = csv.reader(StringIO(content))
    try:
        header = [str(h).strip() for h in next(reader)]
    except StopIteration:
        print("[WARN] TCN probability CSV is empty")
        return 0
    rows = list(reader)

    indices = _select_tcn_indices(header)
    if indices is None:
        print(f"[WARN] Cannot detect columns for TCN probability CSV: {header}")
        return 0

    # Fallback timeline in case source CSV does not contain time column.
    hourly_times = (
        db.query(BasePredictionData.record_time)
        .order_by(BasePredictionData.record_time.asc())
        .all()
    )
    hourly_time_list = []
    seen_hours = set()
    for (record_time,) in hourly_times:
        hour_key = record_time.replace(minute=0, second=0, microsecond=0)
        if hour_key not in seen_hours:
            seen_hours.add(hour_key)
            hourly_time_list.append(hour_key)

    count = 0
    batch_size = 500
    required_cols = [v for k, v in indices.items() if k != "time"]
    max_required = max(required_cols) if required_cols else 0

    for i, row in enumerate(rows):
        if len(row) <= max_required:
            continue

        try:
            if "time" in indices and len(row) > indices["time"]:
                record_time = parse_datetime(row[indices["time"]])
            elif i < len(hourly_time_list):
                record_time = hourly_time_list[i]
            else:
                last_time = hourly_time_list[-1] if hourly_time_list else datetime(2024, 3, 22)
                record_time = last_time + timedelta(hours=i - len(hourly_time_list) + 1)

            record = TcnProbPrediction(
                record_time=record_time,
                real=_safe_float(row[indices["real"]]),
                qr_005=_safe_float(row[indices["qr_005"]]),
                qr_025=_safe_float(row[indices["qr_025"]]),
                qr_05=_safe_float(row[indices["qr_05"]]),
                qr_50=_safe_float(row[indices["qr_50"]]),
                qr_95=_safe_float(row[indices["qr_95"]]),
                qr_975=_safe_float(row[indices["qr_975"]]),
                qr_995=_safe_float(row[indices["qr_995"]]),
            )
            db.add(record)
            count += 1
            if count % batch_size == 0:
                db.commit()
        except Exception as e:
            print(f"[WARN] Failed to parse row in TCN probability CSV: {row}, err={e}")
            continue

    db.commit()
    print(f"[OK] Imported tcn_prob_prediction: {count}")
    return count


def _resolve_import_paths(base_dir: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    base = Path(base_dir)

    price_candidates = (
        str(base / "广东电价数据.csv"),
        str(base / "epf" / "all" / "广东电价数据.csv"),
        str(base / "epf" / "tcn" / "广东电价数据.csv"),
        str(base / "epf" / "mamba" / "广东电价数据.csv"),
        str(base / "epf" / "nlinear" / "广东电价数据.csv"),
    )
    price_csv = _first_existing(price_candidates)

    prediction_candidates = [str(base / "广东电价预测结果.csv")]
    latest_all_pred = _latest_glob(str(base / "epf" / "all" / "results" / "*" / "predictions_test_full.csv"))
    latest_ens_pred = _latest_glob(str(base / "epf" / "ensemble" / "results" / "*" / "predictions_test_full.csv"))
    if latest_all_pred:
        prediction_candidates.append(latest_all_pred)
    if latest_ens_pred:
        prediction_candidates.append(latest_ens_pred)
    prediction_csv = _first_existing(prediction_candidates)

    tcn_candidates = [
        str(base / "epf" / "results" / "sxinput_20260128_213253" / "tcn" / "predictions" / "tcn_predictions_len1.csv"),
    ]
    latest_tcn_week = _latest_glob(str(base / "epf" / "tcn" / "results" / "*" / "predictions_week0.csv"))
    latest_tcn_full = _latest_glob(str(base / "epf" / "tcn" / "results" / "*" / "predictions_test_full.csv"))
    if latest_tcn_week:
        tcn_candidates.append(latest_tcn_week)
    if latest_tcn_full:
        tcn_candidates.append(latest_tcn_full)
    tcn_csv = _first_existing(tcn_candidates)

    return price_csv, prediction_csv, tcn_csv


def import_all_base_data(db: Session, base_dir: str | None = None) -> dict:
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    price_csv, prediction_csv, tcn_csv = _resolve_import_paths(base_dir)
    print(f"[INFO] base price csv: {price_csv}")
    print(f"[INFO] base prediction csv: {prediction_csv}")
    print(f"[INFO] tcn probability csv: {tcn_csv}")

    return {
        "price_data": import_base_price_data(db, price_csv),
        "prediction_data": import_base_prediction_data(db, prediction_csv),
        "tcn_prob_data": import_tcn_prob_data(db, tcn_csv),
    }
