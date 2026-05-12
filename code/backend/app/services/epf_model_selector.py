from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Read model metrics from epf/all results.json
EPF_MODEL_CONFIG = {
    "TCN": "TCN_week",
    "Mamba": "Mamba_week",
    "NLinear": "NLinear_week",
    "Ensemble": "Ensemble_week",
}

# Per-model results.json key mapping (folder-level runs)
EPF_MODEL_RESULTS_KEY = {
    "tcn": "TCN_week",
    "mamba": "Mamba_week",
    "nlinear": "NLinear_week",
    "ensemble": "Ensemble_week",
}

METRIC_WEIGHTS = {
    "MAPE_150": 0.40,  # lower is better
    "MAE": 0.25,       # lower is better
    "RMSE": 0.20,      # lower is better
    "R2": 0.15,        # higher is better
}

DEFAULT_COOLDOWN_SECONDS = 60
DEFAULT_TRAIN_TIMEOUT_SECONDS = 3600


@dataclass
class EpfCandidate:
    model_name: str
    score: float
    metrics: Dict[str, float]
    source_file: str


@dataclass
class EpfSelectionResult:
    selected_model: str
    selected_score: float
    candidates: List[EpfCandidate]
    retrained: bool
    used_cache: bool
    detail: str


def _project_root() -> Path:
    from app.core.config import get_settings
    settings = get_settings()
    
    # 如果配置了 EPF 数据路径，则直接使用该路径（已经是 epf 根目录）
    if settings.epf_data_path:
        return Path(settings.epf_data_path)
    
    # 否则使用默认的项目根目录，并加上 /epf 子目录
    return Path(__file__).resolve().parents[3] / "epf"


def _meta_file() -> Path:
    path = _project_root() / "backend" / "storage" / "epf_auto_train_meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_meta() -> dict:
    path = _meta_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_meta(meta: dict) -> None:
    _meta_file().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_iso_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _latest_all_results_json() -> Path | None:
    root = _project_root() / "all"
    candidates = list(root.glob("results/**/results.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _latest_model_results_json(model_key: str) -> Path | None:
    root = _project_root() / model_key / "results"
    candidates = list(root.glob("**/results.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _normalize_model_key(model_name: str) -> str | None:
    name = model_name.lower()
    if "ensemble" in name or "集成" in model_name or "闆嗘垚" in model_name:
        return "ensemble"
    if "mamba" in name:
        return "mamba"
    if "nlinear" in name:
        return "nlinear"
    if "tcn" in name:
        return "tcn"
    return None


def load_epf_model_metrics(model_name: str) -> tuple[Dict[str, float], str]:
    model_key = _normalize_model_key(model_name)
    if not model_key:
        raise ValueError(f"Unsupported EPF model name: {model_name}")

    latest = _latest_model_results_json(model_key)
    if latest is None:
        raise ValueError(f"No EPF results JSON found for model: {model_name}")

    data = _load_json(latest)
    result_key = EPF_MODEL_RESULTS_KEY.get(model_key)
    if not result_key:
        raise ValueError(f"Unsupported EPF model key: {model_key}")

    metric_block = data.get(result_key)
    if not isinstance(metric_block, dict):
        raise ValueError(f"Missing metrics '{result_key}' in {latest}")

    metrics: Dict[str, float] = {}
    for metric_name in METRIC_WEIGHTS:
        value = metric_block.get(metric_name)
        if isinstance(value, (int, float)):
            metrics[metric_name] = float(value)

    if set(metrics.keys()) != set(METRIC_WEIGHTS.keys()):
        raise ValueError(f"Incomplete metrics in {latest} for {model_name}")

    return metrics, str(latest)


def score_epf_metrics(metrics: Dict[str, float]) -> float:
    # 评分 = 100 * (1 - IMAPE)
    mape_150 = _clamp(metrics["MAPE_150"], 0.0, 2.0)
    score = max(0.0, min(100.0, (1.0 - mape_150) * 100.0))
    return round(score, 6)


def _run_epf_retrain(timeout_seconds: int) -> tuple[bool, str]:
    script = _project_root() / "all" / "epf_predict.py"
    data = _project_root() / "all" / "广东电价数据.csv"
    if not script.exists():
        return False, f"Training script not found: {script}"
    if not data.exists():
        return False, f"Training data not found: {data}"

    cmd = [sys.executable, str(script), "--data", str(data)]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"EPF retraining timed out after {timeout_seconds}s."
    except Exception as exc:  # pragma: no cover - defensive fallback
        return False, f"Failed to execute EPF retraining: {exc}"

    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]
        detail = " | ".join(tail) if tail else "No logs."
        return False, f"EPF retraining failed (code={result.returncode}): {detail}"

    return True, "EPF retraining finished successfully."


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _absolute_metric_score(metrics: Dict[str, float]) -> float:
    # Legacy placeholder to preserve call sites; now only IMAPE is used.
    mape_150 = _clamp(metrics["MAPE_150"], 0.0, 2.0)
    return max(0.0, min(1.0, 1.0 - mape_150))


def _collect_candidates_from_all_results() -> tuple[List[EpfCandidate], str]:
    latest = _latest_all_results_json()
    if latest is None:
        raise ValueError("No EPF all-results JSON found.")

    data = _load_json(latest)
    candidates: List[EpfCandidate] = []

    for model_name, metric_key in EPF_MODEL_CONFIG.items():
        metric_block = data.get(metric_key)
        if not isinstance(metric_block, dict):
            continue

        metrics: Dict[str, float] = {}
        for metric_name in METRIC_WEIGHTS:
            value = metric_block.get(metric_name)
            if isinstance(value, (int, float)):
                metrics[metric_name] = float(value)

        if set(metrics.keys()) != set(METRIC_WEIGHTS.keys()):
            continue

        candidates.append(
            EpfCandidate(
                model_name=model_name,
                score=score_epf_metrics(metrics),
                metrics=metrics,
                source_file=str(latest),
            )
        )

    if not candidates:
        raise ValueError(f"No valid model metrics in: {latest}")

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates, str(latest)


def select_best_epf_model(
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    force_retrain: bool = False,
    train_timeout_seconds: int = DEFAULT_TRAIN_TIMEOUT_SECONDS,
) -> EpfSelectionResult:
    """
    Policy:
    - If called multiple times within cooldown window: reuse current JSON (no retrain).
    - After cooldown: run one retraining attempt, then read latest JSON.
    """
    now = datetime.utcnow()
    meta = _load_meta()
    last_attempt_at = _parse_iso_time(meta.get("last_train_attempt_at"))

    needs_retrain = force_retrain
    if not force_retrain:
        if last_attempt_at is None:
            needs_retrain = True
        else:
            elapsed = (now - last_attempt_at).total_seconds()
            needs_retrain = elapsed >= cooldown_seconds

    retrained = False
    detail = ""

    if needs_retrain:
        ok, msg = _run_epf_retrain(timeout_seconds=train_timeout_seconds)
        meta["last_train_attempt_at"] = now.isoformat()
        if ok:
            retrained = True
            meta["last_retrain_at"] = now.isoformat()
        meta["last_train_message"] = msg
        _save_meta(meta)
        detail = msg
    else:
        detail = f"Within {cooldown_seconds}s cooldown; reused latest JSON result."

    candidates, _ = _collect_candidates_from_all_results()
    selected = candidates[0]
    return EpfSelectionResult(
        selected_model=selected.model_name,
        selected_score=selected.score,
        candidates=candidates,
        retrained=retrained,
        used_cache=not retrained,
        detail=detail,
    )
