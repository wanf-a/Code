#!/usr/bin/env python3
"""
step1_price_prediction.py — ROTS44 电价概率预测
=================================================
模型: TCN-QR, Mamba-QR (简化选择性状态空间), NLinear-QR + 集成
分位数: [0.05, 0.25, 0.5, 0.75, 0.95]
数据: 91天 (20260101~20260401), 65训练 + 12验证 + 14测试

使用方法:
    conda activate epf
    cd ROTS44_delivery/code
    python step1_price_prediction.py

前置条件:
    - summary_timeseries.csv (由数据提取脚本生成)
    - summary_daily.csv (由数据提取脚本生成)
    - PyTorch, sklearn, pandas, matplotlib
"""

import json, os, sys, time, math, warnings, pickle
from copy import deepcopy
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, TensorDataset

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
warnings.filterwarnings("ignore")

# ╔═══════════════════════════════════════════════════════════╗
# ║                        配置                               ║
# ╚═══════════════════════════════════════════════════════════╝
# 自动计算相对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # code/
DELIVERY_DIR = os.path.dirname(SCRIPT_DIR)  # ROTS44_delivery/
PROJECT_ROOT = os.path.dirname(DELIVERY_DIR)  # 项目根目录
CASE_DIR = os.path.join(PROJECT_ROOT, 'Case', 'ROTS 44')  # Case/ROTS 44 (只读数据源)
OUTPUT_DIR = os.path.join(DELIVERY_DIR, 'ROTS 44')  # ROTS44_delivery/ROTS 44 (输出目录)

# 数据源目录（只读）
DATA_DIR = CASE_DIR
SPD        = 96       # 每天96个15分钟时段
TRAIN_DAYS = 77       # 前77天用于训练+验证
VAL_DAYS   = 12       # 其中最后12天做验证
TEST_DAYS  = 14       # 最后14天做测试
QUANTILES  = [0.05, 0.25, 0.5, 0.75, 0.95]
NQ         = len(QUANTILES)
SEED       = 42

# 训练超参
EPOCHS     = 300
PATIENCE   = 40
LR         = 2e-3
WD         = 1e-3
BATCH      = 16
AUG_COPIES = 4       # 训练集噪声增强副本数


# ╔═══════════════════════════════════════════════════════════╗
# ║                      工具函数                              ║
# ╚═══════════════════════════════════════════════════════════╝
def set_seed(s=42):
    torch.manual_seed(s); np.random.seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)

def mape_clipped(yt, yp, lo=150, hi=500):
    yt, yp = np.asarray(yt, float).ravel(), np.asarray(yp, float).ravel()
    denom = np.clip(np.abs(yt), lo, hi)
    return float(np.mean(np.minimum(np.abs(yt - yp) / denom, 1.0)))

def picp(yt, lo, hi):
    yt, lo, hi = (np.asarray(x, float).ravel() for x in (yt, lo, hi))
    return float(np.mean((yt >= lo) & (yt <= hi)))

def pinaw(yt, lo, hi):
    yt, lo, hi = (np.asarray(x, float).ravel() for x in (yt, lo, hi))
    r = yt.max() - yt.min()
    return float(np.mean(hi - lo) / r) if r > 1e-6 else 0.0

def spike_metrics(yt, yp, thr=500):
    yt, yp = np.asarray(yt).ravel(), np.asarray(yp).ravel()
    ts, ps = yt > thr, yp > thr
    tp = (ts & ps).sum()
    recall = tp / ts.sum() if ts.sum() > 0 else float('nan')
    prec   = tp / ps.sum() if ps.sum() > 0 else float('nan')
    return float(recall), float(prec)

def inv_scale(scaler, arr):
    """对任意形状数组做inverse_transform, scaler是fit在(N,1)上的"""
    shape = arr.shape
    return scaler.inverse_transform(arr.reshape(-1, 1)).reshape(shape)

def fwd_scale(scaler, arr):
    shape = arr.shape
    return scaler.transform(arr.reshape(-1, 1)).reshape(shape)

def pf(msg):
    """打印并flush"""
    print(msg, flush=True)


# ╔═══════════════════════════════════════════════════════════╗
# ║                      数据加载                              ║
# ╚═══════════════════════════════════════════════════════════╝
def load_and_prepare():
    pf("=" * 70)
    pf("  [1/6] 加载数据与特征工程")
    pf("=" * 70)

    # 优先从输出目录读取 summary 文件（summary_data.py 生成）
    # 如果不存在，则从 Case 目录读取（向后兼容）
    ts_path = os.path.join(OUTPUT_DIR, 'summary_timeseries.csv')
    daily_path = os.path.join(OUTPUT_DIR, 'summary_daily.csv')
    
    if not os.path.exists(ts_path):
        ts_path = os.path.join(DATA_DIR, 'summary_timeseries.csv')
        pf(f"  从 Case 目录读取: {ts_path}")
    else:
        pf(f"  从输出目录读取: {ts_path}")
    
    if not os.path.exists(daily_path):
        daily_path = os.path.join(DATA_DIR, 'summary_daily.csv')
    
    ts = pd.read_csv(ts_path)
    daily = pd.read_csv(daily_path)

    ts = ts.merge(daily[['day', 'supply_demand_ratio']], on='day', how='left')
    days = sorted(ts['day'].unique())
    assert len(days) == 91, f"期望91天, 实际{len(days)}天"

    all_X, all_y, day_labels = [], [], []

    for day in days:
        dd = ts[ts['day'] == day].sort_values('period')
        assert len(dd) == SPD

        load   = dd['load_MW'].values
        wind   = dd['wind_MW'].values
        solar  = dd['solar_MW'].values
        hydro  = dd['hydro_MW'].values
        price  = dd['price'].values
        sdr    = dd['supply_demand_ratio'].values[0]
        net_ld = load - wind - solar - hydro  # 净负荷

        period = np.arange(SPD, dtype=np.float32)
        hour   = period * 0.25
        dt     = datetime.strptime(str(day), '%Y%m%d')
        dow    = dt.weekday()

        feat = np.column_stack([
            load,                                     #  0 负荷
            wind,                                     #  1 风电
            solar,                                    #  2 光伏
            net_ld,                                   #  3 净负荷
            np.full(SPD, sdr),                        #  4 供需比
            np.sin(2*np.pi*hour/24),                  #  5 sin(hour)
            np.cos(2*np.pi*hour/24),                  #  6 cos(hour)
            np.full(SPD, np.sin(2*np.pi*dow/7)),    #  7 sin(dow)
            np.full(SPD, np.cos(2*np.pi*dow/7)),    #  8 cos(dow)
            np.full(SPD, float(dow >= 5)),             #  9 是否周末
            period / SPD,                              # 10 时段归一位置
        ]).astype(np.float32)

        all_X.append(feat)
        all_y.append(price.astype(np.float32))
        day_labels.append(day)

    all_X = np.stack(all_X)       # (91, 96, 11)
    all_y = np.stack(all_y)       # (91, 96)
    day_labels = np.array(day_labels)
    n_feat = all_X.shape[2]

    pf(f"  特征: {all_X.shape}, 目标: {all_y.shape}, 特征数: {n_feat}")

    # ── 划分 ──
    n_tr  = TRAIN_DAYS - VAL_DAYS   # 65
    n_val = TRAIN_DAYS              # 77
    X_tr, y_tr = all_X[:n_tr],      all_y[:n_tr]
    X_va, y_va = all_X[n_tr:n_val], all_y[n_tr:n_val]
    X_te, y_te = all_X[n_val:],     all_y[n_val:]
    pf(f"  训练{len(X_tr)}天({day_labels[0]}~{day_labels[n_tr-1]})")
    pf(f"  验证{len(X_va)}天({day_labels[n_tr]}~{day_labels[n_val-1]})")
    pf(f"  测试{len(X_te)}天({day_labels[n_val]}~{day_labels[-1]})")

    # ── 归一化 ──
    feat_sc = MinMaxScaler().fit(X_tr.reshape(-1, n_feat))
    tgt_sc  = MinMaxScaler().fit(y_tr.reshape(-1, 1))

    def sc_X(X): return feat_sc.transform(X.reshape(-1, n_feat)).reshape(X.shape).astype(np.float32)
    def sc_y(y): return fwd_scale(tgt_sc, y).astype(np.float32)

    X_tr_s, X_va_s, X_te_s = sc_X(X_tr), sc_X(X_va), sc_X(X_te)
    y_tr_s, y_va_s, y_te_s = sc_y(y_tr), sc_y(y_va), sc_y(y_te)

    # ── 数据增强(训练集加噪声) ──
    aug_X, aug_y = [X_tr_s], [y_tr_s]
    for _ in range(AUG_COPIES):
        noise = np.random.normal(0, 0.02, X_tr_s.shape).astype(np.float32)
        aug_X.append(np.clip(X_tr_s + noise, 0, 1))
        aug_y.append(y_tr_s)
    X_tr_s = np.concatenate(aug_X)
    y_tr_s = np.concatenate(aug_y)
    pf(f"  增强后训练样本: {len(X_tr_s)}天")

    # ── 电价统计 ──
    pf(f"  训练电价: {y_tr.min():.0f}~{y_tr.max():.0f}, 尖峰{(y_tr>500).sum()}/{y_tr.size}({(y_tr>500).mean()*100:.1f}%)")
    pf(f"  测试电价: {y_te.min():.0f}~{y_te.max():.0f}, 尖峰{(y_te>500).sum()}/{y_te.size}({(y_te>500).mean()*100:.1f}%)")

    return {
        'X_tr': X_tr_s, 'y_tr': y_tr_s,
        'X_va': X_va_s, 'y_va': y_va_s,
        'X_te': X_te_s, 'y_te': y_te_s,
        'y_tr_raw': y_tr, 'y_va_raw': y_va, 'y_te_raw': y_te,
        'all_y_raw': all_y,
        'feat_sc': feat_sc, 'tgt_sc': tgt_sc,
        'n_feat': n_feat, 'day_labels': day_labels,
    }


# ╔═══════════════════════════════════════════════════════════╗
# ║                    Pinball Loss                           ║
# ╚═══════════════════════════════════════════════════════════╝
class PinballLoss(nn.Module):
    def __init__(self, quantiles):
        super().__init__()
        self.register_buffer('q', torch.FloatTensor(quantiles))

    def forward(self, pred, target):
        """pred: (B,T,NQ), target: (B,T)"""
        diff = target.unsqueeze(-1) - pred
        return torch.max(self.q * diff, (self.q - 1) * diff).mean()


# ╔═══════════════════════════════════════════════════════════╗
# ║                     模型定义                               ║
# ╚═══════════════════════════════════════════════════════════╝

# ────── TCN-QR ──────
class TCNBlock(nn.Module):
    def __init__(self, ic, oc, k, dilation, drop):
        super().__init__()
        pad = (k - 1) * dilation
        self.conv1 = nn.Conv1d(ic, oc, k, padding=pad, dilation=dilation)
        self.conv2 = nn.Conv1d(oc, oc, k, padding=pad, dilation=dilation)
        self.act   = nn.GELU()
        self.drop  = nn.Dropout(drop)
        self.res   = nn.Conv1d(ic, oc, 1) if ic != oc else nn.Identity()
        self.norm  = nn.BatchNorm1d(oc)

    def forward(self, x):
        T = x.size(2)
        r = self.res(x)
        h = self.drop(self.act(self.conv1(x)[:, :, :T]))
        h = self.drop(self.act(self.conv2(h)[:, :, :T]))
        return self.norm(h + r)

class TCN_QR(nn.Module):
    def __init__(self, n_feat, nq=NQ, chs=(32,32,32), k=3, drop=0.3):
        super().__init__()
        layers = []
        ic = n_feat
        for i, oc in enumerate(chs):
            layers.append(TCNBlock(ic, oc, k, 2**i, drop))
            ic = oc
        self.tcn  = nn.Sequential(*layers)
        self.head = nn.Linear(chs[-1], nq)

    def forward(self, x):
        # x: (B,T,F)
        h = self.tcn(x.transpose(1, 2)).transpose(1, 2)  # (B,T,C)
        return self.head(h)


# ────── Mamba-QR (简化选择性状态空间模型) ──────
class SelectiveSSM(nn.Module):
    """
    简化的 Selective State Space Model (Mamba S6核心机制).
    选择性参数(dt, B, C)由输入决定, 实现输入依赖的序列建模.
    参考: Gu & Dao, "Mamba: Linear-Time Sequence Modeling with Selective State Spaces", 2023
    """
    def __init__(self, d_model, d_state=16, d_conv=4):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state

        # 1D卷积(局部特征)
        self.conv = nn.Conv1d(d_model, d_model, d_conv,
                              padding=d_conv-1, groups=d_model)

        # 选择性参数投影
        self.proj_dt = nn.Linear(d_model, d_model, bias=True)
        self.proj_B  = nn.Linear(d_model, d_state, bias=False)
        self.proj_C  = nn.Linear(d_model, d_state, bias=False)

        # 可学习的A矩阵(log空间, 保证负定)
        A = torch.arange(1, d_state + 1, dtype=torch.float32).unsqueeze(0).expand(d_model, -1)
        self.A_log = nn.Parameter(torch.log(A))

        # 跳跃连接参数
        self.D = nn.Parameter(torch.ones(d_model))

        self.norm = nn.LayerNorm(d_model)

    def forward(self, x):
        """x: (B, T, D) → (B, T, D)"""
        B, T, D = x.shape
        residual = x

        # 局部卷积
        xc = self.conv(x.transpose(1, 2))[:, :, :T].transpose(1, 2)
        xc = F.silu(xc)

        # 选择性参数(输入依赖)
        dt = F.softplus(self.proj_dt(xc))   # (B, T, D) 时间步长
        B_inp = self.proj_B(xc)                  # (B, T, N) 输入矩阵
        C_inp = self.proj_C(xc)                  # (B, T, N) 输出矩阵
        A = -torch.exp(self.A_log)               # (D, N) 状态矩阵(负定)

        # 离散化 + 选择性扫描
        h = torch.zeros(B, D, self.d_state, device=x.device, dtype=x.dtype)
        outputs = []

        for t in range(T):
            dt_t = dt[:, t, :].unsqueeze(-1)               # (B, D, 1)
            dA = torch.exp(A.unsqueeze(0) * dt_t)           # (B, D, N)
            dB = dt_t * B_inp[:, t, :].unsqueeze(1)         # (B, D, N)
            x_t = xc[:, t, :].unsqueeze(-1)                 # (B, D, 1)

            h = dA * h + dB * x_t                            # (B, D, N)
            y_t = (h * C_inp[:, t, :].unsqueeze(1)).sum(-1)  # (B, D)
            y_t = y_t + self.D * xc[:, t, :]                 # skip
            outputs.append(y_t)

        out = torch.stack(outputs, dim=1)  # (B, T, D)
        return self.norm(out + residual)

class Mamba_QR(nn.Module):
    """
    Mamba-QR: 基于选择性状态空间的分位数回归模型.
    架构: 输入投影 → 2层SSM → 输出头
    """
    def __init__(self, n_feat, nq=NQ, d_model=64, d_state=16, n_layers=2, drop=0.3):
        super().__init__()
        self.proj_in = nn.Sequential(nn.Linear(n_feat, d_model), nn.GELU())
        self.layers = nn.ModuleList([
            SelectiveSSM(d_model, d_state) for _ in range(n_layers)
        ])
        self.drop = nn.Dropout(drop)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(), nn.Dropout(drop),
            nn.Linear(d_model, nq)
        )

    def forward(self, x):
        h = self.proj_in(x)
        for layer in self.layers:
            h = self.drop(layer(h))
        return self.head(h)


# ────── NLinear-QR ──────
class NLinear_QR(nn.Module):
    """归一化线性: 去除最后一个值的偏移后做线性映射"""
    def __init__(self, n_feat, nq=NQ):
        super().__init__()
        self.linear = nn.Linear(n_feat, nq)
        nn.init.xavier_uniform_(self.linear.weight)

    def forward(self, x):
        return self.linear(x)


# ╔═══════════════════════════════════════════════════════════╗
# ║                      训练循环                              ║
# ╚═══════════════════════════════════════════════════════════╝
def warmup_cosine_lr(opt, epoch, warmup, total, base_lr, min_lr=1e-6):
    if epoch < warmup:
        lr = base_lr * (epoch + 1) / warmup
    else:
        prog = (epoch - warmup) / max(1, total - warmup)
        lr = min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * prog))
    for pg in opt.param_groups:
        pg['lr'] = lr
    return lr


def train_one_model(model, data, name, dev):
    model = model.to(dev)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    pf(f"\n  训练 {name} | 参数: {n_params:,}")

    tr_dl = DataLoader(
        TensorDataset(torch.from_numpy(data['X_tr']), torch.from_numpy(data['y_tr'])),
        batch_size=BATCH, shuffle=True, drop_last=True
    )
    va_dl = DataLoader(
        TensorDataset(torch.from_numpy(data['X_va']), torch.from_numpy(data['y_va'])),
        batch_size=64
    )

    opt     = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    loss_fn = PinballLoss(QUANTILES).to(dev)

    best_vl, best_st, wait = float('inf'), None, 0
    t0 = time.time()

    for ep in range(EPOCHS):
        lr = warmup_cosine_lr(opt, ep, 5, EPOCHS, LR)

        # --- train ---
        model.train()
        tr_loss = []
        for xb, yb in tr_dl:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tr_loss.append(loss.item())

        # --- val ---
        model.eval()
        vl_loss = []
        with torch.no_grad():
            for xb, yb in va_dl:
                xb, yb = xb.to(dev), yb.to(dev)
                vl_loss.append(loss_fn(model(xb), yb).item())

        tl, vl = np.mean(tr_loss), np.mean(vl_loss)

        if vl < best_vl - 1e-6:
            best_vl = vl
            best_st = deepcopy(model.state_dict())
            wait = 0
            tag = " ★"
        else:
            wait += 1
            tag = ""

        if ep < 5 or ep % 30 == 0 or tag:
            if ep < 10 or ep % 30 == 0 or (tag and ep % 10 == 0):
                pf(f"    Ep {ep+1:3d} | T:{tl:.5f} V:{vl:.5f} lr={lr:.1e} | {time.time()-t0:.0f}s{tag}")

        if wait >= PATIENCE:
            pf(f"    EarlyStopped @ ep {ep+1}")
            break

    if best_st:
        model.load_state_dict(best_st)
    pf(f"    完成 {name}: {time.time()-t0:.0f}s, best_val={best_vl:.5f}")
    return model


@torch.no_grad()
def predict_quantiles(model, X, dev):
    """返回 (N, T, NQ)"""
    model.eval()
    dl = DataLoader(TensorDataset(torch.from_numpy(X)),
                    batch_size=64, shuffle=False)
    parts = []
    for (xb,) in dl:
        parts.append(model(xb.to(dev)).cpu().numpy())
    return np.concatenate(parts)


# ╔═══════════════════════════════════════════════════════════╗
# ║                      评估函数                              ║
# ╚═══════════════════════════════════════════════════════════╝
def evaluate(name, pq_scaled, y_raw, tgt_sc):
    """
    pq_scaled: (N,96,NQ) 归一化空间
    y_raw: (N,96) 原始电价
    返回: results字典, pq_inv(N,96,NQ)反归一化
    """
    N, T, Q = pq_scaled.shape
    # 逐分位数反归一化
    pq_inv = np.zeros_like(pq_scaled)
    for qi in range(Q):
        pq_inv[:, :, qi] = inv_scale(tgt_sc, pq_scaled[:, :, qi])

    qi50 = QUANTILES.index(0.5)
    yt = y_raw.ravel()
    yp = pq_inv[:, :, qi50].ravel()

    r = {}
    r['MAPE_150'] = mape_clipped(yt, yp, 150, 500)
    r['MAPE_200'] = mape_clipped(yt, yp, 200, 500)
    r['RMSE']     = float(np.sqrt(mean_squared_error(yt, yp)))
    r['MAE']      = float(mean_absolute_error(yt, yp))
    r['R2']       = float(r2_score(yt, yp))

    sr, sp = spike_metrics(yt, yp, 500)
    r['spike_recall'] = sr
    r['spike_prec']   = sp

    # 90%区间: q0.05 ~ q0.95
    lo90 = pq_inv[:, :, QUANTILES.index(0.05)].ravel()
    hi90 = pq_inv[:, :, QUANTILES.index(0.95)].ravel()
    r['PICP90']  = picp(yt, lo90, hi90)
    r['PINAW90'] = pinaw(yt, lo90, hi90)

    # 50%区间: q0.25 ~ q0.75
    lo50 = pq_inv[:, :, QUANTILES.index(0.25)].ravel()
    hi50 = pq_inv[:, :, QUANTILES.index(0.75)].ravel()
    r['PICP50']  = picp(yt, lo50, hi50)

    pf(f"  {name:12s} | MAPE150={r['MAPE_150']:.4f} MAPE200={r['MAPE_200']:.4f} "
       f"RMSE={r['RMSE']:.1f} R²={r['R2']:.4f} "
       f"Spike_R={sr:.3f} PICP90={r['PICP90']:.3f}")

    return r, pq_inv


# ╔═══════════════════════════════════════════════════════════╗
# ║                      绘图函数                              ║
# ╚═══════════════════════════════════════════════════════════╝
COLORS = {"TCN":"#e74c3c", "Mamba":"#3498db", "NLinear":"#f39c12", "Ensemble":"#2ecc71"}

def plot_single_day(path, y_true, pq_day, name, day_label):
    qi50 = QUANTILES.index(0.5)
    qi05 = QUANTILES.index(0.05)
    qi95 = QUANTILES.index(0.95)
    c = COLORS.get(name, '#999')

    fig, ax = plt.subplots(figsize=(16, 5))
    xt = np.arange(SPD)
    ax.plot(xt, y_true, 'k-', lw=1.5, label='真实值', zorder=5)
    ax.plot(xt, pq_day[:, qi50], '-', color=c, lw=1.2, label=f'{name} 中位数')
    ax.fill_between(xt, pq_day[:, qi05], pq_day[:, qi95],
                    alpha=0.2, color=c, label='90%置信区间')
    spike = y_true > 500
    if spike.any():
        ax.scatter(xt[spike], y_true[spike], c='red', s=30, zorder=6, label='尖峰')
    ax.set_xticks(range(0, SPD+1, 8))
    ax.set_xticklabels([f'{i*15//60:02d}:00' for i in range(0, SPD+1, 8)], fontsize=8)
    ma = mape_clipped(y_true, pq_day[:, qi50], 150, 500)
    ax.set_title(f'{name}-QR {day_label} | MAPE={ma:.4f}', fontsize=13)
    ax.set_ylabel('电价(元/MWh)'); ax.legend(frameon=False); ax.grid(alpha=0.3)
    ax.set_ylim(bottom=0)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_compare_day(path, y_true, all_pq, day_label):
    qi50 = QUANTILES.index(0.5)
    fig, ax = plt.subplots(figsize=(16, 5))
    xt = np.arange(SPD)
    ax.plot(xt, y_true, 'k-', lw=2, label='真实值', zorder=10)
    for nm, pq in all_pq.items():
        c = COLORS.get(nm, '#999')
        ls = '--' if nm == 'Ensemble' else '-'
        lw = 1.8 if nm == 'Ensemble' else 1.0
        ax.plot(xt, pq[:, qi50], ls, color=c, lw=lw, label=nm, alpha=0.8)
    ax.set_xticks(range(0, SPD+1, 8))
    ax.set_xticklabels([f'{i*15//60:02d}:00' for i in range(0, SPD+1, 8)], fontsize=8)
    ax.set_title(f'模型对比 {day_label}', fontsize=13)
    ax.set_ylabel('电价(元/MWh)'); ax.legend(ncol=2, frameon=False); ax.grid(alpha=0.3)
    ax.set_ylim(bottom=0)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_overview(path, y_true_all, ens_pq_all, results, test_days):
    qi50 = QUANTILES.index(0.5)
    qi05 = QUANTILES.index(0.05)
    qi95 = QUANTILES.index(0.95)

    yt = y_true_all.ravel()
    p50 = ens_pq_all[:, :, qi50].ravel()
    p05 = ens_pq_all[:, :, qi05].ravel()
    p95 = ens_pq_all[:, :, qi95].ravel()
    xt = np.arange(len(yt))

    fig, axes = plt.subplots(2, 1, figsize=(18, 10))

    # 上: 时序图
    axes[0].plot(xt, yt, 'k-', lw=0.8, label='真实值')
    axes[0].plot(xt, p50, '-', color=COLORS['Ensemble'], lw=0.6, label='集成预测')
    axes[0].fill_between(xt, p05, p95, alpha=0.15, color=COLORS['Ensemble'])
    for d in range(1, len(test_days)):
        axes[0].axvline(d * SPD, color='gray', ls=':', alpha=0.3)
    axes[0].set_title('集成模型 - 测试期14天预测', fontsize=13)
    axes[0].legend(frameon=False); axes[0].set_ylabel('电价(元/MWh)'); axes[0].grid(alpha=0.2)

    # 下: 散点图
    colors = ['red' if t > 500 else 'steelblue' for t in yt]
    axes[1].scatter(yt, p50, s=5, alpha=0.5, c=colors)
    axes[1].plot([0, 900], [0, 900], 'k--', lw=0.8)
    axes[1].set_xlabel('真实电价'); axes[1].set_ylabel('预测电价')
    r2 = results['Ensemble']['R2']
    axes[1].set_title(f'散点图(红=尖峰) | R²={r2:.4f}'); axes[1].grid(alpha=0.3)

    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


# ╔═══════════════════════════════════════════════════════════╗
# ║                        MAIN                               ║
# ╚═══════════════════════════════════════════════════════════╝
def main():
    pf("=" * 70)
    pf("  ROTS44 电价概率预测 — Step 1")
    pf("  模型: TCN-QR · Mamba-QR(SSM) · NLinear-QR + 集成")
    pf("  分位数: " + str(QUANTILES))
    pf("=" * 70)

    set_seed(SEED)
    dev = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    pf(f"  设备: {dev}")

    tag = time.strftime("%m%d_%H%M%S")
    out_dir = os.path.join(OUTPUT_DIR, f'step1_out_{tag}')
    os.makedirs(out_dir, exist_ok=True)
    pf(f"  输出: {out_dir}")

    # ── 1. 数据 ──
    data = load_and_prepare()
    tsc    = data['tgt_sc']
    n_feat = data['n_feat']

    # ── 2. 模型定义 ──
    models_def = {
        'TCN':     lambda: TCN_QR(n_feat, NQ, chs=(32,32,32), k=3, drop=0.3),
        'Mamba':   lambda: Mamba_QR(n_feat, NQ, d_model=64, d_state=16, n_layers=2, drop=0.3),
        'NLinear': lambda: NLinear_QR(n_feat, NQ),
    }

    # ── 3. 训练 ──
    pf(f"\n{'='*70}")
    pf("  [2/6] 训练模型")
    pf(f"{'='*70}")

    trained = {}
    test_pq_inv = {}   # name → (14, 96, NQ) 原始尺度
    all_results = {}

    for mn, mfn in models_def.items():
        pf(f"\n  ── {mn}-QR ──")
        m = train_one_model(mfn(), data, f'{mn}-QR', dev)
        trained[mn] = m

        # 测试集预测
        pq = predict_quantiles(m, data['X_te'], dev)   # (14,96,NQ) scaled
        res, pq_inv = evaluate(f'{mn}-QR', pq, data['y_te_raw'], tsc)

        all_results[mn] = res
        test_pq_inv[mn] = pq_inv

        # 保存权重
        torch.save(m.state_dict(), os.path.join(out_dir, f'{mn}_QR.pt'))
        m.cpu(); torch.cuda.empty_cache()

    # ── 4. 集成权重搜索 ──
    pf(f"\n{'='*70}")
    pf("  [3/6] 集成权重搜索(验证集)")
    pf(f"{'='*70}")

    mnames = list(trained.keys())
    val_pq_inv = {}
    for mn in mnames:
        model = trained[mn].to(dev)
        vp = predict_quantiles(model, data['X_va'], dev)
        _, vp_inv = evaluate(f'{mn}-QR(val)', vp, data['y_va_raw'], tsc)
        val_pq_inv[mn] = vp_inv
        model.cpu(); torch.cuda.empty_cache()

    qi50 = QUANTILES.index(0.5)
    best_w, best_mape = None, float('inf')
    for w0 in np.arange(0, 1.01, 0.1):
        for w1 in np.arange(0, 1.01 - w0, 0.1):
            w2 = round(1.0 - w0 - w1, 2)
            if w2 < -0.01:
                continue
            ws = [w0, w1, w2]
            ens = sum(w * val_pq_inv[mn] for w, mn in zip(ws, mnames))
            p50 = ens[:, :, qi50]
            m = mape_clipped(data['y_va_raw'], p50, 150, 500)
            if m < best_mape:
                best_mape = m
                best_w = dict(zip(mnames, ws))

    pf(f"  最优权重: {', '.join(f'{k}={v:.1f}' for k,v in best_w.items())}")
    pf(f"  验证MAPE(150-500): {best_mape:.4f}")

    # 集成测试集
    ens_inv = sum(best_w[mn] * test_pq_inv[mn] for mn in mnames)
    test_pq_inv['Ensemble'] = ens_inv

    # 评估集成(需要将inv转回scaled)
    N, T, Q = ens_inv.shape
    ens_scaled = np.zeros_like(ens_inv)
    for qi in range(Q):
        ens_scaled[:, :, qi] = fwd_scale(tsc, ens_inv[:, :, qi])
    ens_res, _ = evaluate('Ensemble', ens_scaled, data['y_te_raw'], tsc)
    all_results['Ensemble'] = ens_res

    # ── 5. 绘图 ──
    pf(f"\n{'='*70}")
    pf("  [4/6] 绘图")
    pf(f"{'='*70}")

    test_start = TRAIN_DAYS
    test_days = data['day_labels'][test_start:]

    for di in range(len(test_days)):
        dl = test_days[di]
        yt_day = data['y_te_raw'][di]

        # 每个模型单独画
        for mn in test_pq_inv:
            plot_single_day(
                os.path.join(out_dir, f'{mn}_{dl}.png'),
                yt_day, test_pq_inv[mn][di], mn, dl
            )

        # 多模型对比
        plot_compare_day(
            os.path.join(out_dir, f'compare_{dl}.png'),
            yt_day, {mn: test_pq_inv[mn][di] for mn in test_pq_inv}, dl
        )

    # 总览图
    plot_overview(
        os.path.join(out_dir, 'overview.png'),
        data['y_te_raw'], ens_inv, all_results, test_days
    )

    # ── 6. 保存结果 ──
    pf(f"\n{'='*70}")
    pf("  [5/6] 保存结果")
    pf(f"{'='*70}")

    # 结果汇总表
    pf(f"\n  {'模型':12s} {'MAPE150':>8s} {'MAPE200':>8s} {'RMSE':>7s} {'R²':>7s} {'尖峰R':>6s} {'PICP90':>7s}")
    for mn in ['TCN', 'Mamba', 'NLinear', 'Ensemble']:
        r = all_results[mn]
        sr = r.get('spike_recall', float('nan'))
        pf(f"  {mn+'-QR' if mn!='Ensemble' else 'Ensemble':12s} "
           f"{r['MAPE_150']:>8.4f} {r['MAPE_200']:>8.4f} {r['RMSE']:>7.1f} "
           f"{r['R2']:>7.4f} {sr:>6.3f} {r['PICP90']:>7.3f}")

    # JSON
    save_obj = {
        'quantiles': QUANTILES,
        'train_days': TRAIN_DAYS, 'val_days': VAL_DAYS, 'test_days': TEST_DAYS,
        'ensemble_weights': {k: float(v) for k, v in best_w.items()},
        'results': {mn: {k: (float(v) if not (isinstance(v,float) and math.isnan(v)) else None)
                        for k, v in r.items()}
                   for mn, r in all_results.items()},
    }
    with open(os.path.join(out_dir, 'results.json'), 'w') as f:
        json.dump(save_obj, f, indent=2, ensure_ascii=False)

    # 预测CSV(供Step2使用)
    rows = []
    for di in range(len(test_days)):
        d = test_days[di]
        for t in range(SPD):
            row = {'day': d, 'period': t, 'true_price': float(data['y_te_raw'][di, t])}
            for mn in test_pq_inv:
                for qi, q in enumerate(QUANTILES):
                    row[f'{mn}_q{q}'] = float(test_pq_inv[mn][di, t, qi])
            rows.append(row)

    pred_df = pd.DataFrame(rows)
    pred_df.to_csv(os.path.join(out_dir, 'test_predictions.csv'), index=False)
    # 同时保存到输出目录根目录，供 Step2 使用
    pred_df.to_csv(os.path.join(OUTPUT_DIR, 'price_predictions.csv'), index=False)

    # Scalers
    with open(os.path.join(out_dir, 'scalers.pkl'), 'wb') as f:
        pickle.dump({'feat_sc': data['feat_sc'], 'tgt_sc': tsc}, f)

    # 额外: 保存全部91天的预测(训练+验证+测试), 供Step2竞价策略使用
    pf(f"\n  生成全量91天预测(供Step2使用)...")
    all_X_raw = []
    
    # 优先从输出目录读取
    ts_path = os.path.join(OUTPUT_DIR, 'summary_timeseries.csv')
    daily_path = os.path.join(OUTPUT_DIR, 'summary_daily.csv')
    if not os.path.exists(ts_path):
        ts_path = os.path.join(DATA_DIR, 'summary_timeseries.csv')
    if not os.path.exists(daily_path):
        daily_path = os.path.join(DATA_DIR, 'summary_daily.csv')
    
    ts = pd.read_csv(ts_path)
    daily = pd.read_csv(daily_path)
    ts = ts.merge(daily[['day', 'supply_demand_ratio']], on='day', how='left')
    days = sorted(ts['day'].unique())

    for day in days:
        dd = ts[ts['day']==day].sort_values('period')
        load = dd['load_MW'].values; wind = dd['wind_MW'].values
        solar = dd['solar_MW'].values; hydro = dd['hydro_MW'].values
        sdr = dd['supply_demand_ratio'].values[0]
        net_ld = load - wind - solar - hydro
        period = np.arange(SPD, dtype=np.float32)
        hour = period * 0.25
        dt_obj = datetime.strptime(str(day), '%Y%m%d')
        dow = dt_obj.weekday()

        feat = np.column_stack([
            load, wind, solar, net_ld, np.full(SPD, sdr),
            np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
            np.full(SPD, np.sin(2*np.pi*dow/7)), np.full(SPD, np.cos(2*np.pi*dow/7)),
            np.full(SPD, float(dow>=5)), period/SPD,
        ]).astype(np.float32)
        all_X_raw.append(feat)

    all_X_raw = np.stack(all_X_raw)
    all_X_scaled = data['feat_sc'].transform(all_X_raw.reshape(-1, n_feat)).reshape(91, 96, n_feat).astype(np.float32)

    all91_pq = {}
    for mn in mnames:
        model = trained[mn].to(dev)
        pq = predict_quantiles(model, all_X_scaled, dev)
        N, T, Q = pq.shape
        pq_inv = np.zeros_like(pq)
        for qi in range(Q):
            pq_inv[:, :, qi] = inv_scale(tsc, pq[:, :, qi])
        all91_pq[mn] = pq_inv
        model.cpu(); torch.cuda.empty_cache()

    ens91 = sum(best_w[mn] * all91_pq[mn] for mn in mnames)

    # 保存
    all91_rows = []
    for di, day in enumerate(days):
        for t in range(SPD):
            row = {'day': day, 'period': t, 'true_price': float(data['all_y_raw'][di, t])}
            for qi, q in enumerate(QUANTILES):
                row[f'Ensemble_q{q}'] = float(ens91[di, t, qi])
            # 也保存各单模型的中位数
            for mn in mnames:
                row[f'{mn}_q0.5'] = float(all91_pq[mn][di, t, qi50])
            all91_rows.append(row)

    all91_df = pd.DataFrame(all91_rows)
    all91_path = os.path.join(OUTPUT_DIR, 'price_predictions_all91.csv')
    all91_df.to_csv(all91_path, index=False)
    pf(f"  保存: {all91_path} ({len(all91_df)} rows)")

    # ── 完成 ──
    pf(f"\n{'='*70}")
    pf("  [6/6] 完成!")
    pf(f"{'='*70}")
    pf(f"  输出目录: {out_dir}")
    pf(f"  结果文件:")
    for fn in sorted(os.listdir(out_dir)):
        sz = os.path.getsize(os.path.join(out_dir, fn)) / 1024
        pf(f"    {fn} ({sz:.0f}KB)")
    pf(f"\n  供Step2使用:")
    pf(f"    {OUTPUT_DIR}/price_predictions.csv     (测试期14天)")
    pf(f"    {OUTPUT_DIR}/price_predictions_all91.csv (全部91天)")
    pf(f"\n  ✓ Step 1 完成, 可以执行 Step 2")


if __name__ == '__main__':
    main()