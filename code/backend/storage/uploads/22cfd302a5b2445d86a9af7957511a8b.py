import argparse
import json
import math
import os
import time
import warnings
from copy import deepcopy

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, TensorDataset

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
warnings.filterwarnings("ignore")

SPD = 96
QUANTILES = [0.005, 0.025, 0.05, 0.5, 0.95, 0.975, 0.995]
NQ = len(QUANTILES)
COLORS = {
    "Mamba": "#3498db"
}


def mape_clipped(y_true, y_pred, low=200, high=None):
    yt = np.clip(np.asarray(y_true).flatten(), low, None if high is None else high)
    yp = np.clip(np.asarray(y_pred).flatten(), low, None if high is None else high)
    return float(np.mean(np.minimum(np.abs(yt - yp) / yt, 1.0)))


def picp(y_true, lower, upper):
    yt = np.asarray(y_true).flatten()
    lo = np.asarray(lower).flatten()
    hi = np.asarray(upper).flatten()
    return float(np.mean((yt >= lo) & (yt <= hi)))


def pinaw(y_true, lower, upper):
    yt = np.asarray(y_true).flatten()
    lo = np.asarray(lower).flatten()
    hi = np.asarray(upper).flatten()
    r = np.max(yt) - np.min(yt)
    if r < 1e-6:
        return 0.0
    return float(np.mean(hi - lo) / r)


def winkler_score(y_true, lower, upper, alpha=0.1):
    yt = np.asarray(y_true).flatten()
    lo = np.asarray(lower).flatten()
    hi = np.asarray(upper).flatten()
    width = hi - lo
    penalty_low = (2.0 / alpha) * (lo - yt) * (yt < lo)
    penalty_high = (2.0 / alpha) * (yt - hi) * (yt > hi)
    return float(np.mean(width + penalty_low + penalty_high))


def compute_all_metrics(y_true, pred_quantiles, tgt_scaler):
    if pred_quantiles.ndim == 3:
        N, T, Q = pred_quantiles.shape
        p_inv = tgt_scaler.inverse_transform(
            pred_quantiles.reshape(-1, Q)).reshape(N, T, Q)
        y_inv = tgt_scaler.inverse_transform(
            y_true.reshape(-1, 1)).reshape(N, T)
    else:
        p_inv = tgt_scaler.inverse_transform(pred_quantiles)
        y_inv = tgt_scaler.inverse_transform(
            y_true.reshape(-1, 1)).flatten()

    qi50 = QUANTILES.index(0.5)
    point = p_inv[:, :, qi50] if p_inv.ndim == 3 else p_inv[:, qi50]

    metrics = {
        "MAPE_150": mape_clipped(y_inv, point, 150),
        "RMSE": float(np.sqrt(mean_squared_error(
            y_inv.flatten(), point.flatten()))),
        "MAE": float(mean_absolute_error(
            y_inv.flatten(), point.flatten())),
        "R2": float(r2_score(y_inv.flatten(), point.flatten())),
    }

    intervals = [
        (0.05, 0.95, 0.90),
        (0.025, 0.975, 0.95),
        (0.005, 0.995, 0.99),
    ]
    for q_lo, q_hi, level in intervals:
        i_lo = QUANTILES.index(q_lo)
        i_hi = QUANTILES.index(q_hi)
        if p_inv.ndim == 3:
            lo, hi = p_inv[:, :, i_lo], p_inv[:, :, i_hi]
        else:
            lo, hi = p_inv[:, i_lo], p_inv[:, i_hi]

        lvl = int(level * 100)
        metrics[f"PICP_{lvl}"] = picp(y_inv, lo, hi)
        metrics[f"PINAW_{lvl}"] = pinaw(y_inv, lo, hi)
        metrics[f"Winkler_{lvl}"] = winkler_score(
            y_inv, lo, hi, alpha=1-level)

    return metrics, y_inv, p_inv


def load_csv(path):
    for enc in ["gbk", "gb18030", "utf-8"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"无法读取文件: {path}")


def build_features(df, time_col="时间"):
    dt = pd.to_datetime(df[time_col])
    hour = dt.dt.hour + dt.dt.minute / 60.0
    dow = dt.dt.dayofweek

    target = df["电价(元/kWh)"].values.astype(np.float32)

    exo_cols = ["负荷(kW)", "温度(℃)", "风速(m/s)", "云量(%)"]
    exo = [df[c].values.astype(np.float32) for c in exo_cols if c in df.columns]
    exo_mat = np.column_stack(exo) if exo else np.zeros((len(target), 1), np.float32)

    time_feats = np.column_stack([
        np.sin(2 * np.pi * hour / 24),
        np.cos(2 * np.pi * hour / 24),
        np.sin(2 * np.pi * dow / 7),
        np.cos(2 * np.pi * dow / 7),
        np.sin(2 * np.pi * (dt.dt.month - 1) / 12),
        np.cos(2 * np.pi * (dt.dt.month - 1) / 12),
        (dow >= 5).astype(np.float32),
    ]).astype(np.float32)

    feat = np.column_stack([target, exo_mat, time_feats]).astype(np.float32)
    return feat, target, dt, exo_mat


def prepare_data(feat, target, input_len, stride=1,
                 train_ratio=0.7, val_ratio=0.15):
    n = len(feat)
    train_end = int(n * train_ratio)

    feat_scaler = MinMaxScaler()
    feat_scaler.fit(feat[:train_end])
    tgt_scaler = MinMaxScaler()
    tgt_scaler.fit(target[:train_end].reshape(-1, 1))

    feat_scaled = feat_scaler.transform(feat)
    tgt_scaled = tgt_scaler.transform(target.reshape(-1, 1)).flatten()

    max_start = n - input_len - 1
    starts = list(range(0, max_start + 1, stride))
    x = np.zeros((len(starts), input_len, feat.shape[1]), np.float32)
    y = np.zeros(len(starts), np.float32)
    for idx, i in enumerate(starts):
        x[idx] = feat_scaled[i:i + input_len]
        y[idx] = tgt_scaled[i + input_len]

    total = len(starts)
    tr = int(total * train_ratio)
    va = tr + int(total * val_ratio)

    return {
        "x_tr": x[:tr], "y_tr": y[:tr],
        "x_va": x[tr:va], "y_va": y[tr:va],
        "x_te": x[va:], "y_te": y[va:],
        "tgt_scaler": tgt_scaler,
        "feat_scaler": feat_scaler,
        "feat_scaled": feat_scaled,
        "tgt_scaled": tgt_scaled,
        "input_size": feat.shape[1],
        "n_tr": tr, "n_va": va - tr, "n_te": total - va,
        "starts": np.array(starts),
        "tr_start_idx": 0,
        "va_start_idx": tr,
        "te_start_idx": va,
    }


class PinballLoss(nn.Module):
    def __init__(self, quantiles):
        super().__init__()
        self.register_buffer('quantiles', torch.FloatTensor(quantiles))

    def forward(self, pred, target):
        target = target.unsqueeze(-1)
        diff = target - pred
        loss = torch.max(
            self.quantiles * diff,
            (self.quantiles - 1) * diff
        )
        return loss.mean()


class Mamba_QR(nn.Module):
    def __init__(self, input_size, nq=NQ, hidden=128, dropout=0.2):
        super().__init__()
        self.proj_in = nn.Linear(input_size, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=2,
                          batch_first=True, dropout=dropout)
        self.gate = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.Sigmoid()
        )
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, nq)
        )

    def forward(self, x):
        h = self.proj_in(x)
        out, _ = self.gru(h)
        last = out[:, -1, :]
        gated = last * self.gate(last)
        return self.head(gated)


class WarmupCosineScheduler:
    def __init__(self, optimizer, warmup_epochs, total_epochs, min_lr=1e-6):
        self.optimizer = optimizer
        self.warmup = warmup_epochs
        self.total = total_epochs
        self.min_lr = min_lr
        self.base_lr = optimizer.param_groups[0]["lr"]

    def step(self, epoch):
        if epoch < self.warmup:
            lr = self.base_lr * (epoch + 1) / self.warmup
        else:
            progress = (epoch - self.warmup) / max(1, self.total - self.warmup)
            lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * \
                 (1 + math.cos(math.pi * progress))
        for pg in self.optimizer.param_groups:
            pg["lr"] = lr
        return lr


def train_model(model, data, config, name):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    use_cuda = device.type == "cuda"
    train_loader = DataLoader(
        TensorDataset(
            torch.from_numpy(data["x_tr"]),
            torch.from_numpy(data["y_tr"])
        ),
        batch_size=config["batch_size"],
        shuffle=True,
        num_workers=2 if use_cuda else 0,
        pin_memory=use_cuda,
        drop_last=True
    )
    val_loader = DataLoader(
        TensorDataset(
            torch.from_numpy(data["x_va"]),
            torch.from_numpy(data["y_va"])
        ),
        batch_size=config["batch_size"],
        num_workers=2 if use_cuda else 0,
        pin_memory=use_cuda
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["learning_rate"],
        weight_decay=config["weight_decay"]
    )
    scheduler = WarmupCosineScheduler(
        optimizer, config["warmup_epochs"], config["max_epochs"]
    )
    loss_fn = PinballLoss(QUANTILES).to(device)
    scaler = GradScaler()

    best_val = float("inf")
    best_state = None
    patience_counter = 0
    t0 = time.time()

    print(f"\n  训练: {name} | 参数量: {n_params:,} | max_epochs: {config['max_epochs']}")

    for epoch in range(config["max_epochs"]):
        lr = scheduler.step(epoch)

        model.train()
        train_losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            with autocast():
                loss = loss_fn(model(xb), yb)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            train_losses.append(loss.item())

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                with autocast():
                    val_losses.append(loss_fn(model(xb), yb).item())

        train_loss = np.mean(train_losses)
        val_loss = np.mean(val_losses)

        if val_loss < best_val - 1e-6:
            best_val = val_loss
            best_state = deepcopy(model.state_dict())
            patience_counter = 0
            print(f"    Epoch {epoch+1:3d}/{config['max_epochs']} | "
                  f"Train: {train_loss:.6f} Val: {val_loss:.6f} | "
                  f"LR: {lr:.1e} | {time.time()-t0:.0f}s ★")
        else:
            patience_counter += 1
            print(f"    Epoch {epoch+1:3d}/{config['max_epochs']} | "
                  f"Train: {train_loss:.6f} Val: {val_loss:.6f} | "
                  f"LR: {lr:.1e} | {time.time()-t0:.0f}s (patience {patience_counter}/{config['patience']})")
            if patience_counter >= config["patience"]:
                print(f"    早停于 Epoch {epoch+1} (patience={patience_counter})")
                break

    elapsed = time.time() - t0
    print(f"    完成: {elapsed:.0f}s, 最佳验证损失: {best_val:.6f}")

    if best_state:
        model.load_state_dict(best_state)
    return model


def predict_quantiles(model, x, device):
    model.eval()
    predictions = []
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x), torch.zeros(len(x))),
        batch_size=1024,
        num_workers=4,
        pin_memory=True
    )
    with torch.no_grad():
        for xb, _ in loader:
            with autocast():
                predictions.append(
                    model(xb.to(device)).float().cpu().numpy()
                )
    return np.concatenate(predictions)


def rolling_week_predict(model, feat_scaled, input_len, week_starts, device):
    model.eval()
    n_weeks = len(week_starts)
    n_total = len(feat_scaled)
    all_pred = np.zeros((n_weeks, 672, NQ), np.float32)

    for i, start in enumerate(week_starts):
        for t in range(672):
            pos = start + t
            in_start = pos - input_len
            if in_start < 0 or pos >= n_total:
                continue
            x = torch.from_numpy(
                feat_scaled[in_start:pos][np.newaxis]
            ).to(device)
            with torch.no_grad():
                with autocast():
                    all_pred[i, t, :] = model(x).float().cpu().numpy()[0]

    return all_pred


def plot_week_probabilistic(path, true_week, pred_quantiles, name, idx, tgt_scaler):
    hours = np.arange(672) * 0.25

    qi = {q: QUANTILES.index(q) for q in [0.025, 0.05, 0.5, 0.95, 0.975]}
    t_inv = tgt_scaler.inverse_transform(true_week.reshape(-1, 1)).flatten()
    preds = {}
    for q, i in qi.items():
        preds[q] = tgt_scaler.inverse_transform(
            pred_quantiles[:, i].reshape(-1, 1)).flatten()

    color = COLORS.get(name, "#e74c3c")
    ma = mape_clipped(t_inv, preds[0.5])
    cov90 = picp(t_inv, preds[0.05], preds[0.95])
    cov95 = picp(t_inv, preds[0.025], preds[0.975])

    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(hours, t_inv, label='真实值', color='#222', lw=1.8, zorder=5)
    ax.plot(hours, preds[0.5], label=f'{name} 中位数',
            color=color, lw=1.2, zorder=4)
    ax.fill_between(hours, preds[0.05], preds[0.95],
                    alpha=0.25, color=color, label='90% 置信区间')
    ax.fill_between(hours, preds[0.025], preds[0.975],
                    alpha=0.12, color=color, label='95% 置信区间')
    for d in range(1, 7):
        ax.axvline(d * 24, color='gray', ls='--', alpha=0.3)
    ax.set_title(f'{name} 概率预测 (样本#{idx}) | '
                 f'MAPE={ma:.4f} | PICP90={cov90:.3f} | PICP95={cov95:.3f}',
                 fontsize=13)
    ax.set_xlabel('小时')
    ax.set_ylabel('电价 (元/MWh)')
    ax.legend(loc='upper right', frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_day_probabilistic(path, true_day, pred_quantiles, name, idx, tgt_scaler):
    qi = {q: QUANTILES.index(q) for q in [0.05, 0.5, 0.95]}
    t_inv = tgt_scaler.inverse_transform(true_day.reshape(-1, 1)).flatten()
    preds = {}
    for q, i in qi.items():
        preds[q] = tgt_scaler.inverse_transform(
            pred_quantiles[:, i].reshape(-1, 1)).flatten()

    color = COLORS.get(name, "#e74c3c")
    xt = np.arange(SPD)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(xt, t_inv, 'ko-', label='真实值', markersize=3, lw=1.2, zorder=5)
    ax.plot(xt, preds[0.5], 's-', label=f'{name} 预测',
            color=color, markersize=3, lw=1, zorder=4)
    ax.fill_between(xt, preds[0.05], preds[0.95],
                    alpha=0.25, color=color, label='90% 置信区间')
    ax.set_xticks(np.arange(0, SPD + 1, 4))
    ax.set_xticklabels(
        [f'{i*15//60:02d}:{i*15%60:02d}' for i in range(0, SPD + 1, 4)],
        rotation=45, fontsize=8
    )
    ma = mape_clipped(t_inv, preds[0.5])
    ax.set_title(f'{name} 日概率预测 (样本#{idx}) | MAPE={ma:.4f}', fontsize=13)
    ax.set_xlabel('时间')
    ax.set_ylabel('电价 (元/MWh)')
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description="电价概率预测系统")
    parser.add_argument("--data", type=str,
        default="广东电价数据.csv",
        help="数据文件路径")
    parser.add_argument("--input_len", type=int, default=192)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--max_epochs", type=int, default=50)
    parser.add_argument("--learning_rate", type=float, default=5e-4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_dir", type=str, default=None)
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("  广东电力市场电价概率预测系统")
    print(f"  模型: Mamba-QR")
    print(f"  分位数: {QUANTILES}")
    print(f"  输入长度: {args.input_len} ({args.input_len/SPD:.1f}天)")
    print("=" * 70)

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    np.random.seed(args.seed)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")

    if args.output_dir:
        root = args.output_dir
    else:
        root = os.path.join(
            os.path.dirname(args.data), "results",
            time.strftime("prob_%Y%m%d_%H%M%S")
        )
    os.makedirs(root, exist_ok=True)

    df = load_csv(args.data)
    feat, target, dt, exo_mat = build_features(df)
    print(f"\n数据: {len(df):,} 行, 特征维度: {feat.shape[1]}")
    print(f"电价统计: min={target.min():.1f}, max={target.max():.1f}, "
          f"mean={target.mean():.1f} 元/MWh")

    data = prepare_data(feat, target, args.input_len, stride=max(1, args.input_len // 24))
    tsc = data["tgt_scaler"]
    print(f"样本: 训练={data['n_tr']:,}, 验证={data['n_va']:,}, "
          f"测试={data['n_te']:,}")

    config = {
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": 1e-4,
        "warmup_epochs": 3,
        "max_epochs": args.max_epochs,
        "patience": args.patience,
    }

    model_factories = {
        "Mamba": lambda: Mamba_QR(data["input_size"]),
    }

    trained_models = {}
    all_results = {}
    test_preds = {}

    for model_name, factory in model_factories.items():
        model = factory()
        model = train_model(model, data, config, f"{model_name}-QR")

        pq = predict_quantiles(model, data["x_te"], device)
        test_preds[model_name] = pq
        metrics, _, _ = compute_all_metrics(data["y_te"], pq, tsc)

        print(f"\n  {model_name}-QR 测试集结果:")
        print(f"    MAPE(150) = {metrics['MAPE_150']:.4f}")
        print(f"    RMSE = {metrics['RMSE']:.2f} | R² = {metrics['R2']:.4f}")
        print(f"    PICP90 = {metrics['PICP_90']:.3f} | "
              f"PICP95 = {metrics['PICP_95']:.3f}")

        all_results[model_name] = {"direct": metrics}
        trained_models[model_name] = model
        model.cpu()
        torch.cuda.empty_cache()

    # 保存模型权重和 scaler 用于实时推理（放在预测结果保存之前，确保优先输出）
    import pickle
    print(f"\n{'='*70}")
    print(f"  保存模型权重")
    print(f"{'='*70}")
    for mn, mdl in trained_models.items():
        weight_filename = "model_weights.pt" if len(trained_models) == 1 else f"model_weights_{mn}.pt"
        weight_path = os.path.join(root, weight_filename)
        torch.save(mdl.state_dict(), weight_path)
        print(f"  已保存权重: {weight_filename} ({os.path.getsize(weight_path)/1024/1024:.1f} MB)")
    with open(os.path.join(root, "scalers.pkl"), "wb") as f:
        pickle.dump({"feat_scaler": data["feat_scaler"], "tgt_scaler": tsc}, f)
    with open(os.path.join(root, "model_config.json"), "w") as f:
        json.dump({
            "input_size": data["input_size"],
            "input_len": args.input_len,
            "model_type": "mamba",
            "model_class": "Mamba_QR",
            "quantiles": QUANTILES,
            "models": list(trained_models.keys()),
        }, f, indent=2, ensure_ascii=False)
    print(f"  scalers.pkl 和 model_config.json 已保存")

    print(f"\n{'='*70}")
    print(f"  保存完整测试集预测结果")
    print(f"{'='*70}")

    te_start_idx = data["te_start_idx"]
    starts_te = data["starts"][te_start_idx:]
    n_te = len(starts_te)
    rows_te = []
    y_te_inv = tsc.inverse_transform(
        data["y_te"].reshape(-1, 1)).flatten()

    for i in range(n_te):
        time_idx = starts_te[i] + args.input_len
        time_str = str(dt.iloc[time_idx])
        row = {
            "index": i,
            "time": time_str,
            "true": y_te_inv[i]
        }
        for mn in test_preds:
            pq = test_preds[mn][i, :]
            pq_inv = tsc.inverse_transform(
                pq.reshape(-1, 1)).flatten()
            for qi, q in enumerate(QUANTILES):
                row[f"{mn}_q{q}"] = pq_inv[qi]
        rows_te.append(row)

    pd.DataFrame(rows_te).to_csv(
        os.path.join(root, "predictions_test_full.csv"), index=False)
    print(f"  完整测试集预测已保存: predictions_test_full.csv ({n_te} 条记录)")

    print(f"\n{'='*70}")
    print(f"  周前概率预测")
    print(f"{'='*70}")

    n = len(feat)
    feat_scaled = data["feat_scaled"]
    test_start = int(n * 0.85)
    week_starts = list(range(
        test_start,
        n - 672 - args.input_len,
        SPD
    ))[:40]
    n_weeks = len(week_starts)
    print(f"  评估周数: {n_weeks}")

    week_true = np.zeros((n_weeks, 672), np.float32)
    for i, st in enumerate(week_starts):
        if st + 672 <= n:
            week_true[i] = feat_scaled[st:st+672, 0]

    week_preds = {}

    for model_name in trained_models:
        model = trained_models[model_name].to(device)
        wpq = rolling_week_predict(
            model, feat_scaled, args.input_len, week_starts, device
        )
        week_preds[model_name] = wpq

        metrics, _, _ = compute_all_metrics(week_true, wpq, tsc)
        all_results[model_name]["week"] = metrics

        print(f"\n  {model_name}-QR 周前结果:")
        print(f"    MAPE(150) = {metrics['MAPE_150']:.4f}")
        print(f"    PICP90 = {metrics['PICP_90']:.3f} | "
              f"PINAW90 = {metrics['PINAW_90']:.4f}")

        model.cpu()
        torch.cuda.empty_cache()

    print(f"\n  生成图表...")

    qi50 = QUANTILES.index(0.5)
    model_names = list(trained_models.keys())
    plot_indices = [0, n_weeks // 2, n_weeks - 1]

    for wi in plot_indices:
        for mn in week_preds:
            plot_week_probabilistic(
                os.path.join(root, f"week_{mn}_{wi}.png"),
                week_true[wi], week_preds[mn][wi], mn, wi, tsc
            )
            plot_day_probabilistic(
                os.path.join(root, f"day1_{mn}_{wi}.png"),
                week_true[wi, :SPD], week_preds[mn][wi, :SPD],
                mn, wi, tsc
            )

        wt_inv = tsc.inverse_transform(
            week_true[wi].reshape(-1, 1)).flatten()
        hours = np.arange(672) * 0.25
        fig, ax = plt.subplots(figsize=(18, 6))
        ax.plot(hours, wt_inv, label='真实值', color='#222', lw=2, zorder=10)
        for mn in model_names:
            p50 = tsc.inverse_transform(
                week_preds[mn][wi, :, qi50].reshape(-1, 1)).flatten()
            ax.plot(hours, p50, label=mn,
                    color=COLORS[mn], lw=1, alpha=0.7)
        for d in range(1, 7):
            ax.axvline(d * 24, color='gray', ls='--', alpha=0.3)
        ax.set_title(f'Mamba周预测 (样本#{wi})', fontsize=14)
        ax.set_xlabel('小时')
        ax.set_ylabel('电价 (元/MWh)')
        ax.legend(loc='upper right', ncol=2, frameon=False)
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(os.path.join(root, f"week_all_{wi}.png"), dpi=200)
        plt.close(fig)

    if week_preds:
        rows = []
        wt_inv = tsc.inverse_transform(
            week_true[0].reshape(-1, 1)).flatten()
        week_start_idx = week_starts[0]
        for t in range(672):
            time_idx = week_start_idx + t
            time_str = str(dt.iloc[time_idx])
            row = {"step": t, "hour": t * 0.25, "time": time_str, "true": wt_inv[t]}
            for mn in week_preds:
                pq = week_preds[mn][0, t, :]
                pq_inv = tsc.inverse_transform(
                    pq.reshape(-1, 1)).flatten()
                for qi, q in enumerate(QUANTILES):
                    row[f"{mn}_q{q}"] = pq_inv[qi]
            rows.append(row)
        pd.DataFrame(rows).to_csv(
            os.path.join(root, "predictions_week0.csv"), index=False)


    save_results = {}
    for mn, v in all_results.items():
        for scope, metrics in v.items():
            if isinstance(metrics, dict):
                key = f"{mn}_{scope}"
                save_results[key] = {
                    k: (str(vv) if isinstance(vv, dict) else vv)
                    for k, vv in metrics.items()
                }
    with open(os.path.join(root, "results.json"), "w") as f:
        json.dump(save_results, f, indent=2, ensure_ascii=False)

    run_config = {
        "input_len": args.input_len,
        "quantiles": QUANTILES,
        "models": list(model_factories.keys()),
        "train_config": config,
        "data_file": args.data,
        "seed": args.seed,
    }
    with open(os.path.join(root, "config.json"), "w") as f:
        json.dump(run_config, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"  最终汇总")
    print(f"{'='*70}")

    print(f"\n  测试集 Direct 预测结果:")
    print(f"  {'模型':12s} | {'MAPE(150)':>10s} | {'PICP90':>6s} | "
          f"{'PICP95':>6s} | {'PINAW90':>7s} | {'R²':>6s}")
    print(f"  {'-'*12}-+-{'-'*10}-+-{'-'*6}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}")
    for mn in model_names:
        if mn not in all_results or "direct" not in all_results[mn]:
            continue
        r = all_results[mn]["direct"]
        print(f"  {mn:12s} | {r['MAPE_150']:>10.4f} | "
              f"{r['PICP_90']:>6.3f} | {r['PICP_95']:>6.3f} | "
              f"{r['PINAW_90']:>7.4f} | {r['R2']:>6.4f}")

    print(f"\n  周前概率预测结果:")
    print(f"  {'模型':12s} | {'MAPE(150)':>10s} | {'PICP90':>6s} | "
          f"{'PICP95':>6s} | {'PINAW90':>7s} | {'R²':>6s}")
    print(f"  {'-'*12}-+-{'-'*10}-+-{'-'*6}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}")
    for mn in model_names:
        if mn not in all_results or "week" not in all_results[mn]:
            continue
        r = all_results[mn]["week"]
        print(f"  {mn:12s} | {r['MAPE_150']:>10.4f} | "
              f"{r['PICP_90']:>6.3f} | {r['PICP_95']:>6.3f} | "
              f"{r['PINAW_90']:>7.4f} | {r['R2']:>6.4f}")

    print(f"\n  输出目录: {root}")
    print(f"  Done!")


if __name__ == "__main__":
    main()
