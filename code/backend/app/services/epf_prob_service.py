from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from threading import Lock


QUANTILE_TOKENS = {
    "qr_005": "q0.005",
    "qr_025": "q0.025",
    "qr_05": "q0.05",
    "qr_50": "q0.5",
    "qr_95": "q0.95",
    "qr_975": "q0.975",
    "qr_995": "q0.995",
}

_CACHE_LOCK = Lock()
_CSV_CACHE: Dict[str, Dict[str, object]] = {}


def _project_root() -> Path:
    from app.core.config import get_settings
    settings = get_settings()
    
    # 如果配置了 EPF 数据路径，则直接使用该路径（已经是 epf 根目录）
    if settings.epf_data_path:
        return Path(settings.epf_data_path)
    
    # 否则使用默认的项目根目录，并加上 /epf 子目录
    return Path(__file__).resolve().parents[3] / "epf"


def _normalize_model_key(model_name: str) -> str:
    name = model_name.lower()
    if "ensemble" in name or "集成" in model_name or "闆嗘垚" in model_name:
        return "ensemble"
    if "mamba" in name or "manba" in name:
        return "mamba"
    if "nlinear" in name:
        return "nlinear"
    if "tcn" in name:
        return "tcn"
    return name


def _latest_prob_csv(model_key: str, prefer_week: bool = True) -> Path | None:
    root = _project_root() / model_key / "results"
    if prefer_week:
        candidates = list(root.glob("**/predictions_week0.csv"))
        if not candidates:
            candidates = list(root.glob("**/predictions_test_full.csv"))
    else:
        candidates = list(root.glob("**/predictions_test_full.csv"))
        if not candidates:
            candidates = list(root.glob("**/predictions_week0.csv"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_column(headers: Iterable[str], token: str) -> Optional[str]:
    token_lower = token.lower()
    for header in headers:
        cleaned = header.strip().lower()
        if token_lower in cleaned:
            return header
    return None


def _parse_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_csv_rows(csv_path: Path) -> List[Dict[str, float | datetime]]:
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        time_col = _find_column(headers, "time")
        real_col = _find_column(headers, "true") or _find_column(headers, "real") or _find_column(headers, "actual")

        if not time_col or not real_col:
            raise ValueError(f"Missing required columns in {csv_path}")

        quantile_cols: Dict[str, str] = {}
        for key, token in QUANTILE_TOKENS.items():
            found = _find_column(headers, token)
            if found:
                quantile_cols[key] = found

        if "qr_025" not in quantile_cols or "qr_975" not in quantile_cols or "qr_50" not in quantile_cols:
            raise ValueError(f"Missing quantile columns in {csv_path}")

        rows: List[Dict[str, float | datetime]] = []
        for row in reader:
            timestamp = _parse_time(row.get(time_col, ""))
            if not timestamp:
                continue
            real_val = _safe_float(row.get(real_col))
            if real_val is None:
                continue
            entry: Dict[str, float | datetime] = {
                "record_time": timestamp,
                "real": real_val,
            }
            for key, col in quantile_cols.items():
                value = _safe_float(row.get(col))
                if value is not None:
                    entry[key] = value
            rows.append(entry)
    return rows


def _get_cached_rows(csv_path: Path) -> List[Dict[str, float | datetime]]:
    cache_key = str(csv_path)
    mtime = csv_path.stat().st_mtime
    with _CACHE_LOCK:
        cached = _CSV_CACHE.get(cache_key)
        if cached and cached.get("mtime") == mtime:
            return cached["rows"]  # type: ignore[return-value]
    rows = _load_csv_rows(csv_path)
    with _CACHE_LOCK:
        _CSV_CACHE[cache_key] = {"mtime": mtime, "rows": rows}
    return rows


def load_epf_prob_rows(
    model_name: str,
    *,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    prefer_week: bool = False,
) -> tuple[List[Dict[str, float | datetime]], str]:
    model_key = _normalize_model_key(model_name)
    csv_path = _latest_prob_csv(model_key, prefer_week=prefer_week)
    if csv_path is None:
        raise ValueError(f"No probability CSV found for model: {model_name}")

    rows = _get_cached_rows(csv_path)
    if start_time or end_time:
        rows = filter_epf_prob_rows(rows, start_time, end_time)
    return rows, str(csv_path)


def filter_epf_prob_rows(
    rows: List[Dict[str, float | datetime]],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> List[Dict[str, float | datetime]]:
    filtered = []
    for row in rows:
        ts = row.get("record_time")
        if not isinstance(ts, datetime):
            continue
        if start_time and ts < start_time:
            continue
        if end_time and ts > end_time:
            continue
        filtered.append(row)
    return filtered
