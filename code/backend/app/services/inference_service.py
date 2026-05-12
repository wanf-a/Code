"""实时推理服务 - 加载训练好的模型权重进行实时预测"""
from __future__ import annotations

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.base_price_data import BasePriceData
from app.models.dataset_record import DatasetRecord
from app.models.model import Model as ModelEntity
from app.services.training_service import trained_model_dir

QUANTILES = [0.005, 0.025, 0.05, 0.5, 0.95, 0.975, 0.995]
NQ = len(QUANTILES)


# ===== Model Definitions (must match training scripts) =====

class _TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation, dropout):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.residual = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        r = self.residual(x)
        L = r.size(2)
        x = self.drop(self.act(self.conv1(x)[:, :, :L]))
        x = self.drop(self.act(self.conv2(x)[:, :, :L]))
        return x + r


class TCN_QR(nn.Module):
    def __init__(self, input_size, nq=NQ, channels=[64, 64, 64], kernel_size=5, dropout=0.2):
        super().__init__()
        layers = []
        in_ch = input_size
        for i, out_ch in enumerate(channels):
            layers.append(_TCNBlock(in_ch, out_ch, kernel_size, dilation=2**i, dropout=dropout))
            in_ch = out_ch
        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(channels[-1], nq)

    def forward(self, x):
        c = self.backbone(x.transpose(1, 2))
        return self.head(c[:, :, -1])

class Mamba_QR(nn.Module):
    def __init__(self, input_size, nq=NQ, hidden=128, dropout=0.2):
        super().__init__()
        self.proj_in = nn.Linear(input_size, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=2, batch_first=True, dropout=dropout)
        self.gate = nn.Sequential(nn.Linear(hidden, hidden), nn.Sigmoid())
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden), nn.GELU(), nn.Dropout(dropout), nn.Linear(hidden, nq)
        )

    def forward(self, x):
        h = self.proj_in(x)
        out, _ = self.gru(h)
        last = out[:, -1, :]
        gated = last * self.gate(last)
        return self.head(gated)


class NLinear_QR(nn.Module):
    def __init__(self, input_len, nq=NQ):
        super().__init__()
        self.linear = nn.Linear(input_len, nq)
        self.nq = nq
        nn.init.xavier_uniform_(self.linear.weight)

    def forward(self, x):
        price = x[:, :, 0]
        last = price[:, -1:].detach()
        out = self.linear(price - last)
        return out + last.expand(-1, self.nq)


MODEL_CLASSES = {
    "TCN_QR": TCN_QR,
    "Mamba_QR": Mamba_QR,
    "NLinear_QR": NLinear_QR,
}

def _find_latest_weights_dir(model_name: str) -> Optional[Path]:
    """找到模型最新的训练结果目录（包含 model_weights.pt）"""
    settings = get_settings()
    model_dir = trained_model_dir(model_name, settings)
    # 搜索所有子目录中的 model_weights.pt
    candidates = list(model_dir.rglob("model_weights.pt"))
    if not candidates:
        # 对于 ensemble，搜索 model_weights_TCN.pt 等
        candidates = list(model_dir.rglob("model_weights_*.pt"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.parent


def _load_model_artifacts(model_name: str):
    """加载模型权重、scaler 和配置"""
    weights_dir = _find_latest_weights_dir(model_name)
    if weights_dir is None:
        return None

    config_path = weights_dir / "model_config.json"
    scalers_path = weights_dir / "scalers.pkl"

    if not config_path.exists() or not scalers_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        model_config = json.load(f)

    with open(scalers_path, "rb") as f:
        scalers = pickle.load(f)

    model_type = model_config.get("model_type", "")
    model_class_name = model_config.get("model_class", "")
    input_size = model_config["input_size"]
    input_len = model_config["input_len"]

    device = torch.device("cpu")

    if model_type == "ensemble":
        # 加载多个子模型
        sub_models = model_config.get("sub_models", ["TCN", "Mamba", "NLinear"])
        ensemble_weights = model_config.get("ensemble_weights", {})
        loaded_models = {}
        for sub_name in sub_models:
            weight_path = weights_dir / f"model_weights_{sub_name}.pt"
            if not weight_path.exists():
                continue
            if sub_name == "TCN":
                m = TCN_QR(input_size)
            elif sub_name == "Mamba":
                m = Mamba_QR(input_size)
            elif sub_name == "NLinear":
                m = NLinear_QR(input_len)
            else:
                continue
            m.load_state_dict(torch.load(weight_path, map_location=device))
            m.eval()
            loaded_models[sub_name] = m
        return {
            "models": loaded_models,
            "ensemble_weights": ensemble_weights,
            "scalers": scalers,
            "config": model_config,
            "is_ensemble": True,
        }
    else:
        weight_path = weights_dir / "model_weights.pt"
        if not weight_path.exists():
            return None
        cls = MODEL_CLASSES.get(model_class_name)
        if cls is None:
            return None
        if model_class_name == "NLinear_QR":
            model = cls(input_len)
        else:
            model = cls(input_size)
        model.load_state_dict(torch.load(weight_path, map_location=device))
        model.eval()
        return {
            "models": {model_type: model},
            "ensemble_weights": None,
            "scalers": scalers,
            "config": model_config,
            "is_ensemble": False,
        }


def _build_features_from_records(records: list) -> np.ndarray:
    """从数据库记录构建特征矩阵，与训练脚本的 build_features 保持一致"""
    n = len(records)
    feat = np.zeros((n, 12), dtype=np.float32)

    for i, rec in enumerate(records):
        dt = rec.record_time
        hour = dt.hour + dt.minute / 60.0
        dow = dt.weekday()
        month = dt.month

        price = float(rec.price_kwh or 0)
        load = float(rec.load_kw or 0)
        temp = float(rec.temperature or 0)
        wind = float(rec.wind_speed or 0)
        cloud = float(rec.cloud_cover or 0)

        feat[i, 0] = price
        feat[i, 1] = load
        feat[i, 2] = temp
        feat[i, 3] = wind
        feat[i, 4] = cloud
        feat[i, 5] = np.sin(2 * np.pi * hour / 24)
        feat[i, 6] = np.cos(2 * np.pi * hour / 24)
        feat[i, 7] = np.sin(2 * np.pi * dow / 7)
        feat[i, 8] = np.cos(2 * np.pi * dow / 7)
        feat[i, 9] = np.sin(2 * np.pi * (month - 1) / 12)
        feat[i, 10] = np.cos(2 * np.pi * (month - 1) / 12)
        feat[i, 11] = 1.0 if dow >= 5 else 0.0

    return feat


def run_inference(
    db: Session,
    model_name: str,
    dataset_id: int,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict]:
    """加载模型权重，对指定时间范围进行实时推理预测。

    优先从 base_price_data 表取数据（真实电价数据），
    如果没有则回退到 dataset_record 表。

    Returns:
        list of dicts with keys: record_time, real, qr_005, qr_025, qr_05, qr_50, qr_95, qr_975, qr_995
    """
    artifacts = _load_model_artifacts(model_name)
    if artifacts is None:
        raise ValueError(f"未找到模型 '{model_name}' 的权重文件，请先训练模型")

    config = artifacts["config"]
    scalers = artifacts["scalers"]
    feat_scaler = scalers["feat_scaler"]
    tgt_scaler = scalers["tgt_scaler"]
    input_len = config["input_len"]

    # 需要 start_time 之前 input_len 个时间步的历史数据作为输入窗口
    # 每个时间步 15 分钟
    history_minutes = input_len * 15
    history_start = start_time - timedelta(minutes=history_minutes)

    # 优先从 base_price_data 表获取数据（真实电价数据存在这里）
    records = (
        db.query(BasePriceData)
        .filter(
            BasePriceData.record_time >= history_start,
            BasePriceData.record_time <= end_time,
        )
        .order_by(BasePriceData.record_time.asc())
        .all()
    )

    # 如果 base_price_data 没有数据，回退到 dataset_record
    if len(records) < input_len + 1:
        records = (
            db.query(DatasetRecord)
            .filter(
                DatasetRecord.dataset_id == dataset_id,
                DatasetRecord.record_time >= history_start,
                DatasetRecord.record_time <= end_time,
            )
            .order_by(DatasetRecord.record_time.asc())
            .all()
        )

    if len(records) < input_len + 1:
        raise ValueError(
            f"数据不足：需要至少 {input_len + 1} 条记录，"
            f"但只找到 {len(records)} 条（范围 {history_start} 至 {end_time}）"
        )

    # 构建特征矩阵
    feat = _build_features_from_records(records)
    feat_scaled = feat_scaler.transform(feat)

    # 构建真实值映射（用于对比）
    time_to_price = {rec.record_time: float(rec.price_kwh or 0) for rec in records}

    # 找到 start_time 在 records 中的位置
    record_times = [rec.record_time for rec in records]
    start_idx = None
    for i, t in enumerate(record_times):
        if t >= start_time:
            start_idx = i
            break
    if start_idx is None or start_idx < input_len:
        start_idx = input_len

    # 滑动窗口推理
    device = torch.device("cpu")
    results = []

    for pos in range(start_idx, len(records)):
        in_start = pos - input_len
        if in_start < 0:
            continue

        x = torch.from_numpy(feat_scaled[in_start:pos][np.newaxis]).to(device)

        if artifacts["is_ensemble"]:
            # 集成模型：加权平均
            sub_preds = {}
            for sub_name, sub_model in artifacts["models"].items():
                with torch.no_grad():
                    pred = sub_model(x).float().cpu().numpy()[0]
                sub_preds[sub_name] = pred
            weights = artifacts["ensemble_weights"] or {}
            if weights:
                ensemble_pred = sum(
                    weights.get(mn, 1.0 / len(sub_preds)) * sub_preds[mn]
                    for mn in sub_preds
                )
            else:
                ensemble_pred = np.mean(list(sub_preds.values()), axis=0)
            pred_quantiles = ensemble_pred
        else:
            model = list(artifacts["models"].values())[0]
            with torch.no_grad():
                pred_quantiles = model(x).float().cpu().numpy()[0]

        # 反归一化
        pred_inv = tgt_scaler.inverse_transform(
            pred_quantiles.reshape(1, -1)
        ).flatten()

        rec_time = record_times[pos]
        real_price = time_to_price.get(rec_time, 0.0)

        results.append({
            "record_time": rec_time,
            "real": real_price,
            "qr_005": float(pred_inv[0]),
            "qr_025": float(pred_inv[1]),
            "qr_05": float(pred_inv[2]),
            "qr_50": float(pred_inv[3]),
            "qr_95": float(pred_inv[4]),
            "qr_975": float(pred_inv[5]),
            "qr_995": float(pred_inv[6]),
        })

        # 只返回 end_time 之前的数据
        if rec_time >= end_time:
            break

    return results


def has_model_weights(model_name: str) -> bool:
    """检查模型是否有保存的权重文件"""
    return _find_latest_weights_dir(model_name) is not None
