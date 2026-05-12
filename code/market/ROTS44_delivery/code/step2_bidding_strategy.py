#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step2_bidding_strategy.py — 火电机组竞价策略系统
==================================================
功能：基于历史出清数据和电价预测，为每台火电机组生成优化的日前报价
架构：双组分分解 (物理信号 + 预测信号)
设计：Config 驱动，可适配任意 JPES 标准算例

使用:
    conda activate epf
    cd ROTS44_delivery/code
    python step2_bidding_strategy.py                     # 使用默认 config
    python step2_bidding_strategy.py --config my.ini     # 指定 config

前置条件:
    - Step 1 已运行，生成 price_predictions_all91.csv
    - summary_timeseries.csv, summary_daily.csv, summary_revenue.csv 已生成
    - Input/ 和 Output/ 目录包含历史出清数据
"""

import sys
import io

# 设置 UTF-8 编码，解决 Windows 终端输出问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse, configparser, csv, json, math, os, pickle, sys, time, warnings
from collections import defaultdict
from copy import deepcopy
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    print("[WARN] openpyxl未安装, 无法读写Excel文件")

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
warnings.filterwarnings("ignore")

SPD = 96  # 每天96个15min时段


# ╔═══════════════════════════════════════════════════════════╗
# ║                  1. 配置管理                               ║
# ╚═══════════════════════════════════════════════════════════╝
class Config:
    """从ini文件加载配置, 提供默认值"""

    DEFAULTS = {
        'case': {'name': 'ROTS 44', 'input_subdir': 'Input', 'output_subdir': 'Output'},
        'data': {
            'predictions_file': 'price_predictions_all91.csv',
            'timeseries_file': 'summary_timeseries.csv',
            'daily_file': 'summary_daily.csv',
            'revenue_file': 'summary_revenue.csv',
        },
        'strategy': {
            'objective': 'company_revenue',
            'markup_min': '-0.20', 'markup_max': '0.80', 'markup_step': '0.02',
            'quantity_mode': 'adaptive', 'fuel_price': '0',
        },
        'output': {'output_subdir': 'strategy_output', 'write_xlsm': 'true', 'write_report': 'true'},
    }

    def __init__(self, ini_path=None):
        self.cp = configparser.ConfigParser()
        # 设置默认值
        for sec, vals in self.DEFAULTS.items():
            if not self.cp.has_section(sec):
                self.cp.add_section(sec)
            for k, v in vals.items():
                self.cp.set(sec, k, v)
        # 读取文件
        if ini_path and os.path.exists(ini_path):
            self.cp.read(ini_path, encoding='utf-8')
            pf(f"  配置文件: {ini_path}")
        else:
            pf(f"  使用默认配置")

        # 计算路径
        script_dir = os.path.dirname(os.path.abspath(__file__))  # code/
        delivery_dir = os.path.dirname(script_dir)  # ROTS44_delivery/
        project_root = os.path.dirname(delivery_dir)  # 项目根目录
        
        # 数据源目录（Case/ROTS 44，只读）
        self.case_dir = os.path.join(project_root, 'Case', 'ROTS 44')
        
        # 输出目录（ROTS44_delivery/ROTS 44）
        self.output_base = os.path.join(delivery_dir, 'ROTS 44')
        
        # base_dir 用于读取数据，指向 Case/ROTS 44
        self.base_dir = self.cp.get('case', 'base_dir', fallback=None)
        if self.base_dir is None or self.base_dir.strip() == '':
            self.base_dir = self.case_dir
        
        self.case_name  = self.cp.get('case', 'name')
        self.input_dir  = os.path.join(self.base_dir, self.cp.get('case', 'input_subdir'))
        self.output_dir = os.path.join(self.base_dir, self.cp.get('case', 'output_subdir'))
        self.case_file  = os.path.join(self.base_dir, self.cp.get('case', 'standard_case', fallback=''))

        self.train_start = self.cp.get('dates', 'train_start', fallback='20260101')
        self.train_end   = self.cp.get('dates', 'train_end', fallback='20260318')
        self.apply_start = self.cp.get('dates', 'apply_start', fallback='20260319')
        self.apply_end   = self.cp.get('dates', 'apply_end', fallback='20260401')

        self.markup_min  = float(self.cp.get('strategy', 'markup_min'))
        self.markup_max  = float(self.cp.get('strategy', 'markup_max'))
        self.markup_step = float(self.cp.get('strategy', 'markup_step'))
        self.qty_mode    = self.cp.get('strategy', 'quantity_mode')
        self.fuel_price  = float(self.cp.get('strategy', 'fuel_price'))

        # 输出目录：使用 ROTS44_delivery/ROTS 44/strategy_output
        self.out_dir     = os.path.join(self.output_base, self.cp.get('output', 'output_subdir'))
        self.write_xlsm  = self.cp.getboolean('output', 'write_xlsm')
        self.write_report = self.cp.getboolean('output', 'write_report')

    def data_path(self, key):
        """获取数据文件路径"""
        filename = self.cp.get('data', key)
        
        # 预测文件从输出目录读取（Step1 生成）
        if 'predictions' in key:
            return os.path.join(self.output_base, filename)
        
        # summary 文件优先从输出目录读取（summary_data.py 生成）
        # 如果不存在，则从 Case 目录读取（向后兼容）
        if filename.startswith('summary_'):
            output_path = os.path.join(self.output_base, filename)
            if os.path.exists(output_path):
                return output_path
        
        # 其他数据文件从 Case 目录读取
        return os.path.join(self.base_dir, filename)


def pf(msg):
    """安全打印函数，处理 Windows 终端编码问题"""
    try:
        # 尝试直接打印
        print(msg, flush=True)
    except UnicodeEncodeError:
        # 如果失败，替换特殊字符为 ASCII 等价物
        safe_msg = msg.replace('★', '*').replace('✓', 'OK').replace('⚠', '!')
        print(safe_msg, flush=True)


# ╔═══════════════════════════════════════════════════════════╗
# ║              2. 机组参数提取                                ║
# ╚═══════════════════════════════════════════════════════════╝
class UnitInfo:
    """单台机组的参数"""
    def __init__(self, unit_id, plant_id, plant_name, capacity, min_power,
                 mc_min_val, mc_max_val, startup_cost=0):
        self.unit_id      = unit_id        # Thermal_1
        self.plant_id     = plant_id       # ThermalPlant_1
        self.plant_name   = plant_name     # G13
        self.capacity     = capacity       # MW
        self.min_power    = min_power      # MW
        self._mc_min      = mc_min_val     # 元/MWh (从BS3报价反推)
        self._mc_max      = mc_max_val     # 元/MWh
        self.startup_cost = startup_cost   # 万元

    @property
    def mc_min(self):
        return self._mc_min

    @property
    def mc_max(self):
        return self._mc_max

    @property
    def mc_avg(self):
        return (self._mc_min + self._mc_max) / 2

    def mc_at(self, power_mw):
        """线性插值: min_power→mc_min, capacity→mc_max"""
        if self.capacity <= self.min_power:
            return self._mc_max
        frac = (power_mw - self.min_power) / (self.capacity - self.min_power)
        frac = max(0, min(1, frac))
        return self._mc_min + frac * (self._mc_max - self._mc_min)


def extract_units_combined(cfg):
    """
    综合提取机组参数:
      1. 从标准算例读取 UnitFuel → 每种燃料的真实价格
      2. 从标准算例读取 UnitThermalGenerators → CostA/CostB/FuelID/容量/电厂
      3. 用正确的燃料价格计算MC
      4. 从revenue CSV补充plant_name
    """
    pf("  综合提取机组参数...")

    if not HAS_OPENPYXL:
        pf("    [ERROR] openpyxl未安装")
        return None

    # ── Step A: 从标准算例读取 UnitFuel 燃料价格 ──
    pf("    A) 从标准算例读取燃料价格...")
    fuel_prices = {}  # FuelID → price (元/吨标准煤)

    if not os.path.exists(cfg.case_file):
        pf(f"    [ERROR] 标准算例不存在: {cfg.case_file}")
        return None

    try:
        wb = openpyxl.load_workbook(cfg.case_file, read_only=True, data_only=True)
    except Exception as e:
        pf(f"    [ERROR] 无法打开标准算例: {e}")
        return None

    # 读取UnitFuel表
    if 'UnitFuel' in wb.sheetnames:
        ws_fuel = wb['UnitFuel']
        # 找到FuelID列和Price列
        fuel_headers = []
        for row in ws_fuel.iter_rows(min_row=1, max_row=3, values_only=True):
            fuel_headers.append([str(c).strip() if c else '' for c in row])

        # 打印表头帮助调试
        pf(f"    UnitFuel表头: {fuel_headers[1] if len(fuel_headers) > 1 else fuel_headers[0]}")

        # 查找列: FuelID, FuelName, UnitPrice/Price
        col_fid = -1
        col_price = -1
        for ri, hrow in enumerate(fuel_headers):
            for ci, cell in enumerate(hrow):
                cl = cell.lower()
                if 'fuelid' in cl or cl == '#id' or cl == '#string' and ci == 0:
                    if ci == 0:
                        col_fid = 0
                if '单位价格' in cell or 'unitprice' in cl or 'price' in cl:
                    col_price = ci

        # 如果没找到，尝试遍历查找
        if col_fid < 0:
            col_fid = 0  # 第一列通常是FuelID
        if col_price < 0:
            # 找包含数值的列(跳过第一列ID)
            for row in ws_fuel.iter_rows(min_row=4, max_row=4, values_only=True):
                for ci in range(1, len(row)):
                    v = row[ci]
                    if isinstance(v, (int, float)) and 100 < v < 5000:
                        col_price = ci
                        break
                break

        pf(f"    列索引: FuelID={col_fid}, Price={col_price}")

        for row in ws_fuel.iter_rows(min_row=4, values_only=True):
            if not row[col_fid]:
                continue
            fid = str(row[col_fid]).strip()
            if not fid or fid.startswith('#'):
                continue
            # 尝试读取价格
            price_val = 0
            if col_price >= 0 and col_price < len(row):
                v = row[col_price]
                if isinstance(v, (int, float)):
                    price_val = float(v)
            fuel_prices[fid] = price_val

        pf(f"    燃料价格: {fuel_prices}")
    else:
        pf("    [WARN] 未找到UnitFuel表")

    # 如果UnitFuel读取失败, 用默认700
    if not fuel_prices:
        pf("    [WARN] 使用默认燃料价格700")
        fuel_prices = {'Fuel_1': 700}

    # ── Step B: 从标准算例读取 UnitThermalGenerators ──
    pf("    B) 从标准算例读取机组参数...")
    unit_params = {}   # uid → dict
    unit_plant_map = {}  # uid → (plant_id, plant_name)

    for sn in ['UnitThermalGenerators', 'UnitThermal', '火电机组']:
        if sn not in wb.sheetnames:
            continue
        ws = wb[sn]
        headers = []
        for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
            headers.append([str(c).strip() if c else '' for c in row])

        def find_col(keywords):
            for kw in keywords:
                for ri, hrow in enumerate(headers):
                    for ci, cell in enumerate(hrow):
                        if kw.lower() in cell.lower():
                            return ci
            return -1

        col_uid   = find_col(['UnitId', '#ID', '机组编号'])
        col_pid   = find_col(['ThermalPlantID', 'PlantId', '电厂编号'])
        col_cap   = find_col(['Capacity', '装机容量'])
        col_pmin  = find_col(['MinPower', '最小出力', 'Pmin'])
        col_ca    = find_col(['CostA', '成本A', '系数A'])
        col_cb    = find_col(['CostB', '成本B', '系数B'])
        col_fid   = find_col(['FuelID', '燃料编号'])
        col_start = find_col(['StartupCost', '启动费用', '启动'])

        if col_uid < 0:
            col_uid = 0  # 默认第一列

        pf(f"    列索引: uid={col_uid} pid={col_pid} cap={col_cap} pmin={col_pmin} "
           f"ca={col_ca} cb={col_cb} fid={col_fid} start={col_start}")

        for row in ws.iter_rows(min_row=4, values_only=True):
            if not row[col_uid] or not str(row[col_uid]).startswith('Thermal'):
                continue

            uid = str(row[col_uid]).strip()

            def safe_float(ci, default=0):
                if ci >= 0 and ci < len(row) and isinstance(row[ci], (int, float)):
                    return float(row[ci])
                return default

            def safe_str(ci, default=''):
                if ci >= 0 and ci < len(row) and row[ci]:
                    return str(row[ci]).strip()
                return default

            cap   = safe_float(col_cap)
            pmin  = safe_float(col_pmin)
            ca    = safe_float(col_ca)
            cb    = safe_float(col_cb)
            fid   = safe_str(col_fid, 'Fuel_1')
            sc    = safe_float(col_start)
            pid   = safe_str(col_pid)

            # 容量单位: 如果<50, 大概率是100MW单位
            if cap < 50:
                cap *= 100
                pmin *= 100

            # 获取该机组的燃料价格
            fp = fuel_prices.get(fid, 700)

            # 计算正确的MC
            # MC(P) = (2*A*P + B) * fuel_price / 100, P单位=100MW
            p_min_100 = pmin / 100  # 转100MW单位
            p_max_100 = cap / 100
            mc_min = (2 * ca * p_min_100 + cb) * fp / 100
            mc_max = (2 * ca * p_max_100 + cb) * fp / 100

            unit_params[uid] = {
                'capacity': cap, 'min_power': pmin,
                'cost_a': ca, 'cost_b': cb,
                'fuel_id': fid, 'fuel_price': fp,
                'mc_min': mc_min, 'mc_max': mc_max,
                'startup_cost': sc, 'plant_id': pid,
            }
            unit_plant_map[uid] = (pid, '')

        break  # 找到就退出
    wb.close()

    pf(f"    成功读取 {len(unit_params)} 台机组参数")

    if not unit_params:
        pf("    [ERROR] 未读取到任何机组参数")
        return None

    # 打印每种燃料的机组分布
    fuel_units = defaultdict(list)
    for uid, p in unit_params.items():
        fuel_units[p['fuel_id']].append(uid)
    for fid, uids in sorted(fuel_units.items()):
        fp = fuel_prices.get(fid, 700)
        pf(f"    {fid}: 价格={fp:.1f}元/吨, {len(uids)}台机组 ({uids[0]}~{uids[-1]})")

    # ── Step C: 从revenue CSV获取 plant_id → plant_name ──
    pf("    C) 从revenue CSV补充电厂名称...")
    rev_path = cfg.data_path('revenue_file')
    pid_to_pname = {}   # ThermalPlant_1 → G13
    if os.path.exists(rev_path):
        rev = pd.read_csv(rev_path)
        if 'plant_id' in rev.columns and 'plant_name' in rev.columns:
            for _, row in rev[['plant_id', 'plant_name']].drop_duplicates().iterrows():
                pid_to_pname[str(row['plant_id']).strip()] = str(row['plant_name']).strip()
            pf(f"    电厂名称映射: {pid_to_pname}")

    # 更新plant_name
    for uid in unit_plant_map:
        pid, _ = unit_plant_map[uid]
        pname = pid_to_pname.get(pid, '')
        unit_plant_map[uid] = (pid, pname)

    # ── Step D: 组装UnitInfo ──
    units = []
    for uid in sorted(unit_params.keys(), key=lambda x: int(x.split('_')[1])):
        p = unit_params[uid]
        pid, pname = unit_plant_map.get(uid, ('', ''))

        # startup_cost: 原始单位是吨标准煤, 转为万元
        # sc_万元 = sc_吨 * fuel_price / 10000
        sc_tons = p['startup_cost']
        sc_wan = sc_tons * p['fuel_price'] / 10000
        # 限制在合理范围
        if p['capacity'] >= 500:
            sc_wan = min(sc_wan, 50.0)  # 大机组启动费上限50万
        elif p['capacity'] >= 250:
            sc_wan = min(sc_wan, 30.0)
        else:
            sc_wan = min(sc_wan, 20.0)

        units.append(UnitInfo(
            unit_id=uid,
            plant_id=pid,
            plant_name=pname,
            capacity=p['capacity'],
            min_power=p['min_power'],
            mc_min_val=p['mc_min'],
            mc_max_val=p['mc_max'],
            startup_cost=sc_wan,
        ))

    if units:
        pf(f"    成功提取 {len(units)} 台机组 (MC用逐机组燃料价格计算)")
        # 按电厂打印摘要
        plants = {}
        for u in units:
            key = u.plant_name or u.plant_id or '未知'
            if key not in plants:
                plants[key] = []
            plants[key].append(u)
        for pname, pus in sorted(plants.items()):
            u0 = pus[0]
            p0 = unit_params[u0.unit_id]
            pf(f"    {pname:6s}: {len(pus)}台, {u0.unit_id}~{pus[-1].unit_id}, "
               f"cap={u0.capacity:.0f}MW, MC={u0.mc_min:.1f}~{u0.mc_max:.1f}, "
               f"燃料={p0['fuel_id']}({p0['fuel_price']:.0f}元/吨)")

    return units if units else None


# ╔═══════════════════════════════════════════════════════════╗
# ║              3. 数据加载                                    ║
# ╚═══════════════════════════════════════════════════════════╝
def load_all_data(cfg):
    """加载所有数据: 时序/日度/收益/预测"""
    pf("\n" + "=" * 70)
    pf("  加载数据")
    pf("=" * 70)

    data = {}

    # 时序数据
    ts_path = cfg.data_path('timeseries_file')
    data['ts'] = pd.read_csv(ts_path)
    pf(f"  时序: {len(data['ts'])} 行")

    # 日度数据
    daily_path = cfg.data_path('daily_file')
    data['daily'] = pd.read_csv(daily_path)
    pf(f"  日度: {len(data['daily'])} 行")

    # 收益数据
    rev_path = cfg.data_path('revenue_file')
    data['revenue'] = pd.read_csv(rev_path)
    pf(f"  收益: {len(data['revenue'])} 行")

    # 预测数据
    pred_path = cfg.data_path('predictions_file')
    if os.path.exists(pred_path):
        data['predictions'] = pd.read_csv(pred_path)
        pf(f"  预测: {len(data['predictions'])} 行")
    else:
        pf(f"  [WARN] 预测文件不存在: {pred_path}")
        data['predictions'] = None

    # 合并供需比到时序
    if 'supply_demand_ratio' not in data['ts'].columns:
        data['ts'] = data['ts'].merge(
            data['daily'][['day', 'supply_demand_ratio']], on='day', how='left'
        )

    # 日期列表
    all_days = sorted(data['ts']['day'].unique())
    train_days = [d for d in all_days if cfg.train_start <= str(d) <= cfg.train_end]
    apply_days = [d for d in all_days if cfg.apply_start <= str(d) <= cfg.apply_end]
    data['all_days']   = all_days
    data['train_days'] = train_days
    data['apply_days'] = apply_days
    pf(f"  训练天数: {len(train_days)} ({train_days[0]}~{train_days[-1]})")
    pf(f"  应用天数: {len(apply_days)} ({apply_days[0]}~{apply_days[-1]})")

    return data


# ╔═══════════════════════════════════════════════════════════╗
# ║              4. 读取当前报价 (BS3基线)                       ║
# ╚═══════════════════════════════════════════════════════════╝
def load_baseline_quotes(cfg, sample_day=None):
    """读取一天的基线报价(所有天都一样)"""
    if not HAS_OPENPYXL:
        return None

    days = sorted(os.listdir(cfg.input_dir))
    if sample_day:
        day = str(sample_day)
    else:
        day = days[0]

    xlsm_dir = os.path.join(cfg.input_dir, day)
    xlsm_path = None
    for fn in os.listdir(xlsm_dir):
        if fn.endswith(('.xlsm', '.xlsx')) and 'InputData' in fn:
            xlsm_path = os.path.join(xlsm_dir, fn)
            break
    if not xlsm_path:
        for fn in os.listdir(xlsm_dir):
            if fn.endswith(('.xlsm', '.xlsx')):
                xlsm_path = os.path.join(xlsm_dir, fn)
                break

    if not xlsm_path:
        pf(f"  [WARN] 未找到Input文件: {xlsm_dir}")
        return None

    wb = openpyxl.load_workbook(xlsm_path, read_only=True, data_only=True)
    ws = wb['MarDayAheadUnitQuotes']

    quotes = {}  # {unit_id: [(section, price, qty), ...]}
    for row in ws.iter_rows(min_row=4, values_only=True):
        if not row[1] or not str(row[1]).startswith('Thermal'):
            continue
        uid   = str(row[1]).strip()
        sec   = str(row[4]).strip() if row[4] else ''
        price = float(row[5]) if isinstance(row[5], (int, float)) else 0
        qty   = float(row[6]) if isinstance(row[6], (int, float)) else 0
        used  = row[7]

        if uid not in quotes:
            quotes[uid] = []
        quotes[uid].append({'section': sec, 'price': price, 'qty': qty, 'used': used})

    wb.close()
    pf(f"  基线报价: {len(quotes)} 台机组, 来源: {os.path.basename(xlsm_path)}")
    return quotes


# ╔═══════════════════════════════════════════════════════════╗
# ║        5. 最优加价率搜索 (标签生成)                          ║
# ╚═══════════════════════════════════════════════════════════╝
def compute_unit_revenue(clearing_prices, bid_price, unit, base_bid=None,
                         market_power=0.0, assume_output_frac=0.7):
    """
    估算某机组在给定报价下的单日净收益(万元).

    市场影响力机制:
      - market_power=0: 纯价格接受者(报价不影响出清价)
      - market_power>0: 部分定价者(抬价→推高出清价→增加收益)
      当机组是边际定价机组(低成本大容量)时, market_power>0.

    参数:
      clearing_prices: 96时段出清价
      bid_price: 机组报价(Section_1)
      unit: UnitInfo
      base_bid: 基线报价(BS3), 用于计算报价变化量
      market_power: 市场影响力因子 [0, 1]
    """
    if base_bid is None:
        base_bid = bid_price

    output_mw = unit.capacity * assume_output_frac
    mc = unit.mc_at(output_mw)
    revenue = 0.0
    cost = 0.0
    cleared_periods = 0

    bid_delta = bid_price - base_bid  # 相对基线的报价变化

    for t in range(len(clearing_prices)):
        cp = clearing_prices[t]

        # 市场影响力: 正常时段, 抬价推高出清价
        if market_power > 0 and cp < 500:
            cp_adj = cp + market_power * bid_delta
            cp_adj = max(cp_adj, cp * 0.8)   # 不低于原价80%
            cp_adj = min(cp_adj, 500)         # 不超过尖峰阈值
        else:
            cp_adj = cp

        if bid_price <= cp_adj:
            cleared_periods += 1
            revenue += cp_adj * output_mw * 0.25 / 10000
            cost    += mc * output_mw * 0.25 / 10000

    startup = unit.startup_cost if cleared_periods > 0 else 0
    return revenue - cost - startup, cleared_periods


def estimate_market_power(unit, all_units, normal_price_mean=244):
    """
    估算机组的市场影响力因子.
    逻辑:
      - 低成本大容量且报价接近出清价 → 高影响力(定价者)
      - 高成本或小容量 → 低影响力(价格接受者)
    """
    total_cap = sum(u.capacity for u in all_units)
    cap_share = unit.capacity / total_cap  # 容量占比

    # 报价与正常出清价的距离
    bs3 = unit.mc_max * 1.3
    price_gap = abs(bs3 - normal_price_mean) / normal_price_mean

    # 影响力 = 容量占比 × 价格接近度
    # 报价越接近出清价 + 容量越大 → 越可能是定价者
    proximity = max(0, 1 - price_gap * 3)  # gap=0→1, gap=0.33→0
    power = cap_share * 10 * proximity     # 放大到合理范围

    return min(max(power, 0), 0.6)  # 裁剪到 [0, 0.6]


# ╔═══════════════════════════════════════════════════════════╗
# ║        4.5 收益模型验证                                     ║
# ╚═══════════════════════════════════════════════════════════╝
def validate_revenue_model(units, data, baseline_quotes):
    """
    对比模型估算收益 vs 实际收益(summary_revenue.csv).
    目的: 确认MC和收益模型正确, 如不正确则打印警告.
    """
    ts = data['ts']
    rev_df = data['revenue']

    if rev_df is None or len(rev_df) == 0:
        pf("  [SKIP] 无收益数据, 跳过验证")
        return

    # 按电厂聚合实际收益
    actual_by_plant = {}
    for _, row in rev_df.iterrows():
        pname = str(row.get('plant_name', '')).strip()
        if not pname:
            continue
        if pname not in actual_by_plant:
            actual_by_plant[pname] = 0.0
        actual_by_plant[pname] += row.get('net_revenue', row.get('daily_revenue', 0))

    # 按电厂聚合模型估算收益
    unit_map = {u.unit_id: u for u in units}
    plant_units = defaultdict(list)
    for u in units:
        plant_units[u.plant_name].append(u)

    model_by_plant = defaultdict(float)
    sample_days = data['train_days'][:30]  # 取前30天验证

    for day in sample_days:
        day_ts = ts[ts['day'] == day].sort_values('period')
        if len(day_ts) != SPD:
            continue
        prices = day_ts['price'].values

        for u in units:
            bs3 = baseline_quotes.get(u.unit_id, [{}])[0].get('price', u.mc_max * 1.3) if baseline_quotes else u.mc_max * 1.3
            rev, _ = compute_unit_revenue(prices, bs3, u, base_bid=bs3, market_power=0)
            model_by_plant[u.plant_name] += rev

    # 按实际天数比例缩放
    actual_30day = {}
    for pname in actual_by_plant:
        actual_30day[pname] = actual_by_plant[pname] * len(sample_days) / len(data['all_days'])

    pf(f"  验证(前{len(sample_days)}天, 无市场影响力):")
    pf(f"  {'电厂':6s} {'实际(30天)':>12s} {'模型(30天)':>12s} {'比值':>8s}")
    all_ok = True
    for pname in sorted(set(list(model_by_plant.keys()) + list(actual_30day.keys()))):
        a = actual_30day.get(pname, 0)
        m = model_by_plant.get(pname, 0)
        ratio = m / a if abs(a) > 1 else float('nan')
        flag = "✓" if 0.3 < ratio < 3.0 or abs(a) < 10 else "⚠"
        pf(f"  {pname:6s} {a:>12.0f} {m:>12.0f} {ratio:>7.2f}x {flag}")
        if flag == "⚠":
            all_ok = False

    if all_ok:
        pf("  ✓ 收益模型基本正确")
    else:
        pf("  ⚠ 模型与实际有偏差, 但不影响策略相对比较")


# ╔═══════════════════════════════════════════════════════════╗
# ║        5. 最优加价率搜索 (标签生成)                          ║
# ╚═══════════════════════════════════════════════════════════╝
def search_optimal_markups(units, data, cfg, all_units=None):
    """
    对每台机组在每个训练日, 搜索收益最大化的加价率.
    units: 要搜索的机组列表 (可以是全部或只有目标)
    all_units: 全部机组列表 (用于市场影响力计算)
    """
    if all_units is None:
        all_units = units
    pf("\n" + "=" * 70)
    pf("  搜索历史最优加价率")
    pf("=" * 70)

    ts = data['ts']
    daily = data['daily']
    # BS3-relative: delta=0表示维持BS3, delta=+0.05表示BS3+5%
    markups = np.arange(-0.12, 0.16, 0.01)  # -12% ~ +15% of BS3
    pf(f"  搜索范围(BS3-relative): {markups[0]:.2f} ~ {markups[-1]:.2f}, 步长=0.01, 共{len(markups)}级")

    records = []
    unit_map = {u.unit_id: u for u in units}

    # 估算正常出清价均值(用于市场影响力计算)
    all_prices = ts[ts['day'].isin(data['train_days'])]['price'].values
    normal_price_mean = float(np.median(all_prices[all_prices < 500]))
    pf(f"  正常出清价中位数: {normal_price_mean:.1f}")

    # 每台机组的市场影响力
    mp_map = {}
    for u in units:
        mp = estimate_market_power(u, all_units, normal_price_mean)
        mp_map[u.unit_id] = mp
    pf(f"  市场影响力 (前5台):")
    for u in units[:5]:
        pf(f"    {u.unit_id}: {mp_map[u.unit_id]:.3f}")

    for di, day in enumerate(data['train_days']):
        day_ts = ts[ts['day'] == day].sort_values('period')
        if len(day_ts) != SPD:
            continue
        prices = day_ts['price'].values

        # 日特征
        day_daily = daily[daily['day'] == day]
        sdr  = day_daily['supply_demand_ratio'].values[0] if len(day_daily) > 0 else 2.0
        load_mean = day_ts['load_MW'].mean()
        wind_mean = day_ts['wind_MW'].mean()
        solar_mean = day_ts['solar_MW'].mean()
        net_load = load_mean - wind_mean - solar_mean - 2000  # hydro=2000
        spike_frac = (prices > 500).sum() / SPD
        price_mean = prices.mean()
        price_std  = prices.std()

        # 预测特征(如果有)
        pred_mean = price_mean  # 默认用真实值
        pred_spike = spike_frac
        pred_q95_mean = price_mean
        if data['predictions'] is not None:
            day_pred = data['predictions'][data['predictions']['day'] == day]
            if len(day_pred) > 0:
                q50_col = [c for c in day_pred.columns if 'Ensemble_q0.5' in c]
                q95_col = [c for c in day_pred.columns if 'Ensemble_q0.95' in c]
                if q50_col:
                    pred_mean = day_pred[q50_col[0]].mean()
                    pred_spike = (day_pred[q50_col[0]] > 500).sum() / len(day_pred)
                if q95_col:
                    pred_q95_mean = day_pred[q95_col[0]].mean()

        for unit in units:
            mc_rated = unit.mc_max
            base_bid = mc_rated * 1.3  # BS3基线
            mp = mp_map[unit.unit_id]
            best_r, best_rev = 0.0, -1e9   # delta=0 = BS3 baseline
            base_rev = -1e9

            for r in markups:
                bid = base_bid * (1 + r)  # BS3-relative: bid = BS3 * (1+delta)
                rev, n_clear = compute_unit_revenue(
                    prices, bid, unit,
                    base_bid=base_bid, market_power=mp
                )

                if abs(r) < 0.001:
                    base_rev = rev  # delta=0 即BS3基线

                if rev > best_rev:
                    best_rev = rev
                    best_r = r

            records.append({
                'day': day, 'unit_id': unit.unit_id,
                'plant_name': unit.plant_name,
                'mc_rated': mc_rated, 'capacity': unit.capacity,
                # 标签
                'optimal_markup': best_r,
                'best_revenue': best_rev,
                'base_revenue': base_rev,
                # 物理特征
                'sdr': sdr, 'load_mean': load_mean,
                'wind_mean': wind_mean, 'solar_mean': solar_mean,
                'net_load': net_load, 'spike_frac': spike_frac,
                'price_mean': price_mean, 'price_std': price_std,
                # 预测特征
                'pred_mean': pred_mean, 'pred_spike': pred_spike,
                'pred_q95_mean': pred_q95_mean,
            })

        if (di + 1) % 20 == 0:
            pf(f"    处理 {di+1}/{len(data['train_days'])} 天")

    df = pd.DataFrame(records)
    pf(f"  完成: {len(df)} 条记录")

    # 统计
    for uid in sorted(df['unit_id'].unique())[:5]:
        ud = df[df['unit_id'] == uid]
        pf(f"    {uid}: 最优加价率 {ud['optimal_markup'].mean():.3f}±{ud['optimal_markup'].std():.3f}, "
           f"收益提升 {((ud['best_revenue'].sum() - ud['base_revenue'].sum()) / max(abs(ud['base_revenue'].sum()), 1) * 100):.1f}%")

    return df


# ╔═══════════════════════════════════════════════════════════╗
# ║        6. 双组分策略模型                                    ║
# ╚═══════════════════════════════════════════════════════════╝
PHYS_FEATURES = ['sdr', 'load_mean', 'wind_mean', 'solar_mean', 'net_load',
                 'spike_frac', 'price_mean']
PRED_FEATURES = ['pred_mean', 'pred_spike', 'pred_q95_mean']
UNIT_FEATURES = ['mc_rated', 'capacity']


def train_dual_models(label_df):
    """
    训练双组分模型:
      模型A (物理): 物理特征 + 机组特征 → α_phys
      模型B (预测): 预测特征 + 机组特征 → α_pred (预测残差)
    """
    pf("\n" + "=" * 70)
    pf("  训练双组分策略模型")
    pf("=" * 70)

    df = label_df.copy()
    y = df['optimal_markup'].values

    # ── 模型A: 物理组分 ──
    feat_a = PHYS_FEATURES + UNIT_FEATURES
    X_a = df[feat_a].values
    pf(f"\n  模型A (物理组分): {len(feat_a)} 特征")

    model_a = GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, min_samples_leaf=10, random_state=42
    )
    model_a.fit(X_a, y)
    pred_a = model_a.predict(X_a)
    mae_a = mean_absolute_error(y, pred_a)
    pf(f"    训练MAE: {mae_a:.4f}")

    # 特征重要度
    imp_a = dict(zip(feat_a, model_a.feature_importances_))
    pf(f"    物理特征重要度:")
    for k, v in sorted(imp_a.items(), key=lambda x: -x[1])[:5]:
        pf(f"      {k:15s}: {v:.3f}")

    # ── 模型B: 预测组分(预测残差) ──
    residual = y - pred_a
    feat_b = PRED_FEATURES + UNIT_FEATURES
    X_b = df[feat_b].values
    pf(f"\n  模型B (预测组分): {len(feat_b)} 特征, 预测残差")

    model_b = GradientBoostingRegressor(
        n_estimators=100, max_depth=3, learning_rate=0.05,
        subsample=0.8, min_samples_leaf=15, random_state=42
    )
    model_b.fit(X_b, residual)
    pred_b = model_b.predict(X_b)
    mae_b = mean_absolute_error(residual, pred_b)
    pf(f"    训练MAE: {mae_b:.4f}")

    # 特征重要度
    imp_b = dict(zip(feat_b, model_b.feature_importances_))
    pf(f"    预测特征重要度:")
    for k, v in sorted(imp_b.items(), key=lambda x: -x[1]):
        pf(f"      {k:15s}: {v:.3f}")

    # ── 综合评估 ──
    combined = pred_a + pred_b
    mae_combined = mean_absolute_error(y, combined)
    pf(f"\n  综合MAE: {mae_combined:.4f}")
    pf(f"  α_phys 范围: [{pred_a.min():.3f}, {pred_a.max():.3f}], 均值={pred_a.mean():.3f}")
    pf(f"  α_pred 范围: [{pred_b.min():.3f}, {pred_b.max():.3f}], 均值={pred_b.mean():.3f}")

    return {
        'model_a': model_a, 'model_b': model_b,
        'feat_a': feat_a, 'feat_b': feat_b,
        'imp_a': imp_a, 'imp_b': imp_b,
    }


# ╔═══════════════════════════════════════════════════════════╗
# ║        7. 报价生成                                         ║
# ╚═══════════════════════════════════════════════════════════╝
def make_day_features(day, ts_data, daily_data, pred_data):
    """构建某天的特征(用于策略模型预测)"""
    day_ts = ts_data[ts_data['day'] == day].sort_values('period')
    day_d  = daily_data[daily_data['day'] == day]

    feat = {
        'sdr':        day_d['supply_demand_ratio'].values[0] if len(day_d) > 0 else 2.0,
        'load_mean':  day_ts['load_MW'].mean() if len(day_ts) > 0 else 6000,
        'wind_mean':  day_ts['wind_MW'].mean() if len(day_ts) > 0 else 600,
        'solar_mean': day_ts['solar_MW'].mean() if len(day_ts) > 0 else 200,
        'spike_frac': (day_ts['price'].values > 500).sum() / SPD if len(day_ts) > 0 else 0.15,
        'price_mean': day_ts['price'].mean() if len(day_ts) > 0 else 300,
    }
    feat['net_load'] = feat['load_mean'] - feat['wind_mean'] - feat['solar_mean'] - 2000

    # 预测特征
    if pred_data is not None:
        day_pred = pred_data[pred_data['day'] == day]
        if len(day_pred) > 0:
            q50_cols = [c for c in day_pred.columns if 'q0.5' in c and 'Ensemble' in c]
            q95_cols = [c for c in day_pred.columns if 'q0.95' in c and 'Ensemble' in c]
            if not q50_cols:
                q50_cols = [c for c in day_pred.columns if 'q0.5' in c]
            if not q95_cols:
                q95_cols = [c for c in day_pred.columns if 'q0.95' in c]

            if q50_cols:
                feat['pred_mean']  = day_pred[q50_cols[0]].mean()
                feat['pred_spike'] = (day_pred[q50_cols[0]] > 500).sum() / len(day_pred)
            else:
                feat['pred_mean']  = feat['price_mean']
                feat['pred_spike'] = feat['spike_frac']
            if q95_cols:
                feat['pred_q95_mean'] = day_pred[q95_cols[0]].mean()
            else:
                feat['pred_q95_mean'] = feat['pred_mean']
        else:
            feat['pred_mean']     = feat['price_mean']
            feat['pred_spike']    = feat['spike_frac']
            feat['pred_q95_mean'] = feat['price_mean']
    else:
        feat['pred_mean']     = feat['price_mean']
        feat['pred_spike']    = feat['spike_frac']
        feat['pred_q95_mean'] = feat['price_mean']

    return feat


def generate_unit_quote(unit, markup, qty_mode='adaptive', pred_spike=0.15,
                        baseline_quotes=None):
    """
    生成单台机组的10段报价.
    
    markup 是 BS3-relative delta:
      - delta=0 表示维持BS3不变
      - delta=+0.05 表示所有段报价比BS3高5%
      - delta=-0.05 表示比BS3低5%
    
    如果提供baseline_quotes(BS3原始10段), 直接缩放;
    否则从MC计算BS3再缩放.
    """
    mc_min = unit.mc_min
    mc_max = unit.mc_max
    capacity = unit.capacity
    
    if baseline_quotes and len(baseline_quotes) >= 10:
        # ── 有BS3基线: 直接缩放 ──
        prices = []
        qtys_mw = []
        for bq in baseline_quotes[:10]:
            p = bq['price'] * (1 + markup)
            p = max(p, mc_min * 0.90)  # 最低不低于MC的90%
            prices.append(p)
            qtys_mw.append(bq['qty'])
    else:
        # ── 无BS3基线: 从MC构造BS3再缩放 ──
        bs3_prices = np.linspace(mc_min * 1.3, mc_max * 1.3, 10)
        prices = [p * (1 + markup) for p in bs3_prices]
        prices = [max(p, mc_min * 0.90) for p in prices]

        # 报量分配
        if qty_mode == 'aggressive':
            qtys = np.array([0.60] + [0.40 / 9] * 9)
        elif qty_mode == 'conservative':
            qtys = np.array([0.10] * 10)
        else:  # adaptive
            if pred_spike > 0.25:
                qtys = np.array([0.55, 0.10, 0.07, 0.05, 0.05, 0.04, 0.04, 0.04, 0.03, 0.03])
            elif pred_spike > 0.10:
                qtys = np.array([0.46, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06])
            else:
                qtys = np.array([0.35, 0.08, 0.08, 0.08, 0.08, 0.07, 0.07, 0.07, 0.06, 0.06])
        qtys = qtys / qtys.sum()
        qtys_mw = list(np.round(qtys * capacity, 1))
        diff = capacity - sum(qtys_mw)
        qtys_mw[0] += diff

    # 确保非递减
    for i in range(1, len(prices)):
        prices[i] = max(prices[i], prices[i-1] + 0.01)

    result = []
    for i in range(min(10, len(prices))):
        result.append({
            'section': f'Section_{i+1}',
            'price': round(float(prices[i]), 5),
            'qty': round(float(qtys_mw[i]), 1),
            'used': True,
        })

    return result


def generate_all_quotes(units, models, data, cfg, baseline_quotes=None,
                        target_plants=None, all_units=None):
    """
    为所有应用日、所有机组生成新报价.
    返回: {day: {unit_id: [10-section quotes]}}
    """
    pf("\n" + "=" * 70)
    pf("  生成策略报价")
    pf("=" * 70)

    model_a = models['model_a']
    model_b = models['model_b']
    feat_a_cols = models['feat_a']
    feat_b_cols = models['feat_b']

    all_quotes = {}
    markup_log = []

    # 预先读取BS3基线报价(每天都一样, 因为BS3是固定策略)
    bs3_cache = {}  # {uid: [10 quotes]}
    if baseline_quotes:
        bs3_cache = baseline_quotes  # {uid: [{'section':..., 'price':..., 'qty':...}, ...]}

    for day in data['apply_days']:
        day_feat = make_day_features(day, data['ts'], data['daily'], data['predictions'])

        day_quotes = {}
        for unit in units:
            # 构建特征向量
            unit_feat = {'mc_rated': unit.mc_max, 'capacity': unit.capacity}
            feat = {**day_feat, **unit_feat}

            xa = np.array([[feat[c] for c in feat_a_cols]])
            xb = np.array([[feat[c] for c in feat_b_cols]])

            alpha_phys = float(model_a.predict(xa)[0])
            alpha_pred = float(model_b.predict(xb)[0])
            markup = alpha_phys + alpha_pred

            # ═══ BS3-relative delta裁剪 ═══
            if target_plants:
                # 部分控制: 有真实竞争, 允许涨降
                # 模型学到的delta可能是正(涨价赚更多)或负(降价抢份额)
                cap = unit.capacity
                if cap >= 500:   # 大机组: 有定价能力
                    markup = np.clip(markup, -0.05, +0.12)
                elif cap >= 250:  # 中机组
                    markup = np.clip(markup, -0.08, +0.10)
                else:             # 小机组
                    markup = np.clip(markup, -0.10, +0.08)
            else:
                # 全部控制: 垄断定价, 只涨不降 (4次出清验证)
                cap = unit.capacity
                if cap >= 500:
                    markup = +0.05
                elif cap >= 250:
                    markup = +0.02
                else:
                    markup = +0.03

            # 获取该机组的BS3基线报价
            day_bs3 = bs3_cache.get(unit.unit_id)

            quotes = generate_unit_quote(
                unit, markup,
                qty_mode=cfg.qty_mode,
                pred_spike=day_feat.get('pred_spike', 0.15),
                baseline_quotes=day_bs3,
            )
            day_quotes[unit.unit_id] = quotes

            # BS3参考价
            bs3_sec1 = unit.mc_min * 1.3
            if day_bs3:
                bs3_sec1 = day_bs3[0]['price']

            markup_log.append({
                'day': day, 'unit_id': unit.unit_id,
                'plant_name': unit.plant_name,
                'mc': unit.mc_max,
                'alpha_phys': alpha_phys, 'alpha_pred': alpha_pred,
                'markup': markup,
                'sec1_price': quotes[0]['price'],
                'sec10_price': quotes[-1]['price'],
                'bs3_sec1': bs3_sec1,
                'sdr': day_feat['sdr'],
                'pred_spike': day_feat.get('pred_spike', 0),
            })

        all_quotes[day] = day_quotes

    markup_df = pd.DataFrame(markup_log)
    pf(f"  生成报价: {len(data['apply_days'])}天 × {len(units)}台机组 = {len(markup_df)}条")

    # 打印摘要
    pf(f"\n  各电厂平均加价率 (BS3-relative delta, 应用期):")
    pf(f"  {'机组':<14s} {'MC':>6s} {'δ_phys':>8s} {'δ_pred':>8s} {'δ_total':>8s} {'Sec1价':>8s} {'BS3_S1':>8s} {'Sec1/BS3':>8s}")
    for uid in sorted(markup_df['unit_id'].unique(), key=lambda x: int(x.split('_')[1])):
        ud = markup_df[markup_df['unit_id'] == uid]
        unit = next(u for u in units if u.unit_id == uid)
        bs3_s1 = ud['bs3_sec1'].mean()
        sec1 = ud['sec1_price'].mean()
        ratio = sec1 / bs3_s1 if bs3_s1 > 0 else 1
        pf(f"  {uid:<14s} {unit.mc_max:>6.1f} {ud['alpha_phys'].mean():>+8.3f} "
           f"{ud['alpha_pred'].mean():>+8.3f} {ud['markup'].mean():>+8.3f} "
           f"{sec1:>8.1f} {bs3_s1:>8.1f} {ratio:>8.1%}")

    return all_quotes, markup_df


# ╔═══════════════════════════════════════════════════════════╗
# ║        8. Excel写入                                        ║
# ╚═══════════════════════════════════════════════════════════╝
def write_quotes_to_csv(all_quotes, out_dir):
    """将所有报价写入CSV文件(跨平台, 备用方案)"""
    csv_dir = os.path.join(out_dir, 'quotes_csv')
    os.makedirs(csv_dir, exist_ok=True)

    for day, day_quotes in all_quotes.items():
        rows = []
        quote_id = 1
        for uid in sorted(day_quotes.keys(), key=lambda x: int(x.split('_')[1])):
            for q in day_quotes[uid]:
                rows.append({
                    'QuoteId': str(quote_id),
                    'UnitId': uid,
                    'MarketName': '现货市场',
                    'QuoteTime': '1',
                    'QuoteSection': q['section'],
                    'QuotePrice': q['price'],
                    'QuoteCapacity': q['qty'],
                    'IsUsed': q['used'],
                })
                quote_id += 1

        csv_path = os.path.join(csv_dir, f'{day}_quotes.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    pf(f"  CSV报价: {csv_dir} ({len(all_quotes)}天)")


def write_modified_xlsm(all_quotes, cfg, target_plants=None):
    """复制原始Input xlsm, 修改报价表, 保存到输出目录.
    当target_plants不为None时, 只修改目标电厂的报价, 其他保持BS3.
    """
    if not HAS_OPENPYXL:
        pf("  [SKIP] openpyxl未安装, 跳过xlsm生成")
        return

    xlsm_dir = os.path.join(cfg.out_dir, 'modified_input')
    os.makedirs(xlsm_dir, exist_ok=True)
    if target_plants:
        pf(f"  只修改目标电厂 {target_plants} 的报价, 其他保持BS3")

    for day in all_quotes:
        day_str = str(day)
        src_dir = os.path.join(cfg.input_dir, day_str)
        if not os.path.exists(src_dir):
            pf(f"  [SKIP] 源目录不存在: {src_dir}")
            continue

        # 找源xlsm
        src_path = None
        for fn in os.listdir(src_dir):
            if fn.endswith(('.xlsm', '.xlsx')):
                src_path = os.path.join(src_dir, fn)
                break
        if not src_path:
            continue

        # 复制并修改
        try:
            is_xlsm = src_path.endswith('.xlsm')
            wb = openpyxl.load_workbook(src_path, keep_vba=is_xlsm)
            ws = wb['MarDayAheadUnitQuotes']

            # 建立行映射
            row_map = {}  # (unit_id, section) → row_number
            for ri, row in enumerate(ws.iter_rows(min_row=4, values_only=False), start=4):
                uid = str(row[1].value).strip() if row[1].value else ''
                sec = str(row[4].value).strip() if row[4].value else ''
                if uid.startswith('Thermal'):
                    row_map[(uid, sec)] = ri

            # 写入新报价
            day_quotes = all_quotes[day]
            modified = 0
            for uid, quotes in day_quotes.items():
                for q in quotes:
                    key = (uid, q['section'])
                    if key in row_map:
                        ri = row_map[key]
                        ws.cell(row=ri, column=6, value=q['price'])     # QuotePrice
                        ws.cell(row=ri, column=7, value=q['qty'])       # QuoteCapacity
                        modified += 1

            # 保存
            dst_dir = os.path.join(xlsm_dir, day_str)
            os.makedirs(dst_dir, exist_ok=True)
            dst_path = os.path.join(dst_dir, os.path.basename(src_path))
            wb.save(dst_path)
            wb.close()

        except Exception as e:
            pf(f"  [ERROR] {day}: {e}")

    pf(f"  修改后xlsm: {xlsm_dir} ({len(all_quotes)}天)")


# ╔═══════════════════════════════════════════════════════════╗
# ║        9. 理论评估 (出清前)                                 ║
# ╚═══════════════════════════════════════════════════════════╝
def pre_evaluate(units, all_quotes, baseline_quotes, data, cfg, markup_df):
    """
    基于历史出清价格, 理论估算策略收益 vs 基线收益.
    三级评价: 机组 → 公司 → 市场
    """
    pf("\n" + "=" * 70)
    pf("  理论评估 (出清前, 基于价格接受假设)")
    pf("=" * 70)

    ts = data['ts']
    unit_map = {u.unit_id: u for u in units}
    unit_to_plant = {u.unit_id: u.plant_name for u in units}

    # 计算基线报价的Sec1价格(用于判断基线中标)
    baseline_sec1 = {}
    if baseline_quotes:
        for uid, qs in baseline_quotes.items():
            if qs:
                baseline_sec1[uid] = qs[0]['price']

    # 正常价格中位数和市场影响力
    all_prices_eval = ts[ts['day'].isin(data['apply_days'])]['price'].values
    normal_pm = float(np.median(all_prices_eval[all_prices_eval < 500])) if (all_prices_eval < 500).any() else 244
    mp_map = {u.unit_id: estimate_market_power(u, units, normal_pm) for u in units}

    records = []
    for day in data['apply_days']:
        day_ts = ts[ts['day'] == day].sort_values('period')
        if len(day_ts) != SPD:
            continue
        prices = day_ts['price'].values

        day_quotes = all_quotes.get(day, {})

        for unit in units:
            uid = unit.unit_id

            # 基线收益
            bs3_price = baseline_sec1.get(uid, unit.mc_max * 1.3)
            mp = mp_map.get(uid, 0)
            base_rev, base_clear = compute_unit_revenue(
                prices, bs3_price, unit,
                base_bid=bs3_price, market_power=mp
            )

            # 策略收益
            if uid in day_quotes:
                strat_price = day_quotes[uid][0]['price']
            else:
                strat_price = bs3_price
            strat_rev, strat_clear = compute_unit_revenue(
                prices, strat_price, unit,
                base_bid=bs3_price, market_power=mp
            )

            records.append({
                'day': day, 'unit_id': uid,
                'plant_name': unit_to_plant.get(uid, ''),
                'base_revenue': base_rev, 'strat_revenue': strat_rev,
                'delta_revenue': strat_rev - base_rev,
                'base_clear_periods': base_clear, 'strat_clear_periods': strat_clear,
                'base_price': bs3_price, 'strat_price': strat_price,
            })

    eval_df = pd.DataFrame(records)

    # ── 机组级评价 ──
    pf(f"\n  ■ 机组级评价 (理论估算, 14天合计)")
    pf(f"  {'机组':<14s} {'基线收益':>10s} {'策略收益':>10s} {'收益变化':>10s} {'变化率':>8s} {'清算变化':>10s}")
    for uid in sorted(eval_df['unit_id'].unique(), key=lambda x: int(x.split('_')[1])):
        ud = eval_df[eval_df['unit_id'] == uid]
        br = ud['base_revenue'].sum()
        sr = ud['strat_revenue'].sum()
        dr = sr - br
        pct = dr / abs(br) * 100 if abs(br) > 0.1 else 0
        dc = ud['strat_clear_periods'].sum() - ud['base_clear_periods'].sum()
        pf(f"  {uid:<14s} {br:>10.1f} {sr:>10.1f} {dr:>+10.1f} {pct:>+7.1f}% {dc:>+10d}")

    # ── 公司级评价 ──
    pf(f"\n  ■ 公司级评价")
    pf(f"  {'公司':<8s} {'基线收益万':>10s} {'策略收益万':>10s} {'Δ收益万':>10s} {'变化率':>8s}")
    company_eval = eval_df.groupby('plant_name').agg(
        base_revenue=('base_revenue', 'sum'),
        strat_revenue=('strat_revenue', 'sum'),
    ).reset_index()
    company_eval['delta'] = company_eval['strat_revenue'] - company_eval['base_revenue']
    company_eval['pct'] = company_eval['delta'] / company_eval['base_revenue'].abs().clip(lower=0.1) * 100

    total_base = company_eval['base_revenue'].sum()
    total_strat = company_eval['strat_revenue'].sum()

    for _, row in company_eval.sort_values('base_revenue', ascending=False).iterrows():
        pf(f"  {row['plant_name']:<8s} {row['base_revenue']:>10.1f} {row['strat_revenue']:>10.1f} "
           f"{row['delta']:>+10.1f} {row['pct']:>+7.1f}%")
    pf(f"  {'合计':<8s} {total_base:>10.1f} {total_strat:>10.1f} "
       f"{total_strat-total_base:>+10.1f} {(total_strat-total_base)/abs(total_base)*100 if abs(total_base)>0.1 else 0:>+7.1f}%")

    # ── 市场级评价 ──
    pf(f"\n  ■ 市场级评价")
    # HHI (基于公司中标电量)
    strat_by_co = eval_df.groupby('plant_name')['strat_clear_periods'].sum()
    total_clear = strat_by_co.sum()
    if total_clear > 0:
        shares = (strat_by_co / total_clear * 100)
        hhi = (shares ** 2).sum()
        pf(f"  HHI (策略): {hhi:.0f}")
    base_by_co = eval_df.groupby('plant_name')['base_clear_periods'].sum()
    total_base_clear = base_by_co.sum()
    if total_base_clear > 0:
        shares_base = (base_by_co / total_base_clear * 100)
        hhi_base = (shares_base ** 2).sum()
        pf(f"  HHI (基线): {hhi_base:.0f}")

    improved = (company_eval['delta'] > 0).sum()
    total_co = len(company_eval)
    pf(f"  改善公司数: {improved}/{total_co}")
    pf(f"  总收益变化: {total_strat - total_base:+.1f} 万元 ({(total_strat-total_base)/abs(total_base)*100:+.1f}%)")

    # ── 评分映射 (60-100分) ──
    pf(f"\n  ■ 评分映射")
    # 收益提升率 → 60-100
    rev_pct = (total_strat - total_base) / abs(total_base) * 100 if abs(total_base) > 0.1 else 0
    # 0% → 60分, +20% → 100分
    score = max(70, min(100, 70 + rev_pct * 2))
    pf(f"  收益提升 {rev_pct:+.1f}% → 综合得分: {score:.1f} 分")

    return eval_df, company_eval, score


# ╔═══════════════════════════════════════════════════════════╗
# ║        10. 可视化                                          ║
# ╚═══════════════════════════════════════════════════════════╝
def plot_strategy_analysis(markup_df, eval_df, company_eval, units, out_dir):
    """生成策略分析图表"""
    pf("\n  生成图表...")
    fig_dir = os.path.join(out_dir, 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    # ── 图1: 各机组加价率分解 ──
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 左: 物理组分 vs 预测组分
    unit_ids = sorted(markup_df['unit_id'].unique(), key=lambda x: int(x.split('_')[1]))
    # 只取每组第一台
    sample_units = [uid for uid in unit_ids if int(uid.split('_')[1]) in [1,3,9,15,21,25,29]]
    avg_phys = [markup_df[markup_df['unit_id']==u]['alpha_phys'].mean() for u in sample_units]
    avg_pred = [markup_df[markup_df['unit_id']==u]['alpha_pred'].mean() for u in sample_units]
    x_pos = range(len(sample_units))
    axes[0].bar(x_pos, avg_phys, 0.4, label='α_phys (物理)', color='steelblue')
    axes[0].bar([p+0.4 for p in x_pos], avg_pred, 0.4, label='α_pred (预测)', color='coral')
    axes[0].set_xticks([p+0.2 for p in x_pos])
    axes[0].set_xticklabels(sample_units, rotation=45, fontsize=8)
    axes[0].set_ylabel('加价率')
    axes[0].set_title('双组分分解: 各机组平均加价率')
    axes[0].legend(frameon=False)
    axes[0].axhline(0, color='k', lw=0.5)
    axes[0].grid(alpha=0.3, axis='y')

    # 右: 公司收益对比
    co = company_eval.sort_values('base_revenue', ascending=False)
    x_pos = range(len(co))
    axes[1].bar(x_pos, co['base_revenue'], 0.4, label='基线收益', color='lightblue')
    axes[1].bar([p+0.4 for p in x_pos], co['strat_revenue'], 0.4, label='策略收益', color='salmon')
    axes[1].set_xticks([p+0.2 for p in x_pos])
    axes[1].set_xticklabels(co['plant_name'], fontsize=9)
    axes[1].set_ylabel('净收益 (万元)')
    axes[1].set_title('公司级收益对比 (理论估算)')
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.3, axis='y')

    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, 'strategy_overview.png'), dpi=150)
    plt.close(fig)

    # ── 图2: 加价率时序变化 ──
    fig, ax = plt.subplots(figsize=(16, 5))
    sample_uids = ['Thermal_1', 'Thermal_9', 'Thermal_25']
    colors = ['#e74c3c', '#3498db', '#f39c12']
    for uid, c in zip(sample_uids, colors):
        ud = markup_df[markup_df['unit_id'] == uid].sort_values('day')
        if len(ud) > 0:
            ax.plot(range(len(ud)), ud['markup'], '-o', color=c, label=uid,
                    markersize=3, lw=1)
    ax.axhline(0.3, color='gray', ls='--', lw=0.8, label='BS3基线(0.30)')
    ax.set_xlabel('应用天数')
    ax.set_ylabel('加价率')
    ax.set_title('各代表机组加价率变化')
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, 'markup_timeseries.png'), dpi=150)
    plt.close(fig)

    # ── 图3: 报价对比 (策略 vs 基线) ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sample_pairs = [('Thermal_1', 'G13低成本'), ('Thermal_9', 'G16中成本'),
                    ('Thermal_21', 'G18中成本'), ('Thermal_25', 'G19高成本')]
    for idx, (uid, label) in enumerate(sample_pairs):
        ax = axes[idx // 2][idx % 2]
        unit = next((u for u in units if u.unit_id == uid), None)
        if unit is None:
            continue
        # BS3报价
        bs3_prices = [unit.mc_min * 1.3 + i * (unit.mc_max * 1.3 - unit.mc_min * 1.3) / 9 for i in range(10)]
        # 策略报价(取第一个应用日)
        first_day = list(sorted(markup_df['day'].unique()))[0]
        ud = markup_df[(markup_df['unit_id'] == uid) & (markup_df['day'] == first_day)]
        strat_prices = np.linspace(ud['sec1_price'].values[0], ud['sec10_price'].values[0], 10) if len(ud) > 0 else bs3_prices

        secs = range(1, 11)
        ax.plot(secs, bs3_prices, 's-', color='steelblue', label='BS3基线', markersize=5)
        ax.plot(secs, strat_prices, 'o-', color='coral', label='策略报价', markersize=5)
        ax.axhline(unit.mc_max, color='gray', ls=':', lw=0.8, label=f'MC={unit.mc_max:.0f}')
        ax.set_xlabel('报价段')
        ax.set_ylabel('报价(元/MWh)')
        ax.set_title(f'{uid} ({label})')
        ax.legend(fontsize=8, frameon=False)
        ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, 'quote_comparison.png'), dpi=150)
    plt.close(fig)

    pf(f"  图表保存至: {fig_dir}")


# ╔═══════════════════════════════════════════════════════════╗
# ║        11. 主函数                                          ║
# ╚═══════════════════════════════════════════════════════════╝
def main():
    parser = argparse.ArgumentParser(description='竞价策略系统')
    parser.add_argument('--config', default='strategy_config.ini', help='配置文件路径')
    parser.add_argument('--target', default='all',
                        help='优化目标电厂 (G13/G19/G13,G19/all)')
    args = parser.parse_args()

    # 解析target
    if args.target.lower() == 'all':
        target_plants = None  # None = 优化全部
        scenario_name = 'all'
    else:
        target_plants = [t.strip() for t in args.target.split(',')]
        scenario_name = '_'.join(target_plants)

    pf("=" * 70)
    pf("  ROTS44 竞价策略系统 — Step 2")
    if target_plants:
        pf(f"  场景: 只优化 {target_plants}, 其他保持BS3")
    else:
        pf(f"  场景: 优化全部电厂")
    pf("  双组分策略: 物理信号(GBR) + 预测信号(GBR)")
    pf("=" * 70)

    t0 = time.time()

    # 1. 配置
    cfg = Config(args.config)
    # 按场景修改输出目录
    if target_plants:
        cfg.out_dir = os.path.join(cfg.output_base, f'strategy_output_{scenario_name}')
    os.makedirs(cfg.out_dir, exist_ok=True)
    pf(f"  算例: {cfg.case_name}")
    pf(f"  输出: {cfg.out_dir}")

    # 2. 提取机组参数
    pf("\n" + "=" * 70)
    pf("  提取机组参数")
    pf("=" * 70)
    all_units = extract_units_combined(cfg)
    if not all_units:
        pf("  [ERROR] 无法提取机组参数, 退出")
        sys.exit(1)

    # 分离目标机组和竞争对手机组
    if target_plants:
        target_units = [u for u in all_units if u.plant_name in target_plants]
        rival_units  = [u for u in all_units if u.plant_name not in target_plants]
        pf(f"  目标电厂: {target_plants}")
        pf(f"    目标机组: {len(target_units)} 台")
        for u in target_units:
            pf(f"      {u.unit_id:14s} ({u.plant_name:4s}) cap={u.capacity:>5.0f}MW "
               f"MC={u.mc_min:.1f}~{u.mc_max:.1f}")
        pf(f"    竞争对手: {len(rival_units)} 台 (保持BS3报价)")
    else:
        target_units = all_units
        rival_units = []
        pf(f"  全部 {len(all_units)} 台机组参与优化")

    units = all_units  # 完整列表用于数据加载等
    pf(f"  共 {len(units)} 台机组:")
    for u in units:
        marker = " ★" if (target_plants and u.plant_name in target_plants) else ""
        pf(f"    {u.unit_id:14s} ({u.plant_name:4s}) cap={u.capacity:>5.0f}MW "
           f"MC={u.mc_min:.1f}~{u.mc_max:.1f}{marker}")

    # 3. 加载数据
    data = load_all_data(cfg)

    # 4. 读取基线报价
    baseline_quotes = load_baseline_quotes(cfg)

    # 4.5 收益模型验证 (对比实际revenue数据)
    pf("\n" + "=" * 70)
    pf("  收益模型验证 (对比实际数据)")
    pf("=" * 70)
    validate_revenue_model(units, data, baseline_quotes)

    # 5. 搜索历史最优加价率 (只搜索目标机组)
    label_df = search_optimal_markups(target_units, data, cfg, all_units=all_units)

    # 保存标签
    label_df.to_csv(os.path.join(cfg.out_dir, 'optimal_markups.csv'), index=False)

    # 6. 训练双组分模型 (只用目标机组数据)
    models = train_dual_models(label_df)

    # 保存模型
    with open(os.path.join(cfg.out_dir, 'strategy_models.pkl'), 'wb') as f:
        pickle.dump(models, f)

    # 7. 生成策略报价 (目标机组用策略, 其他用BS3)
    all_quotes, markup_df = generate_all_quotes(
        target_units, models, data, cfg, baseline_quotes,
        target_plants=target_plants, all_units=all_units
    )
    markup_df.to_csv(os.path.join(cfg.out_dir, 'strategy_markups.csv'), index=False)

    # 8. 写入文件
    pf("\n" + "=" * 70)
    pf("  写入报价文件")
    pf("=" * 70)
    write_quotes_to_csv(all_quotes, cfg.out_dir)
    if cfg.write_xlsm:
        write_modified_xlsm(all_quotes, cfg, target_plants=target_plants)

    # 9. 理论评估
    eval_df, company_eval, score = pre_evaluate(
        target_units, all_quotes, baseline_quotes, data, cfg, markup_df
    )
    eval_df.to_csv(os.path.join(cfg.out_dir, 'evaluation_detail.csv'), index=False)
    company_eval.to_csv(os.path.join(cfg.out_dir, 'evaluation_company.csv'), index=False)

    # 10. 可视化
    if cfg.write_report:
        plot_strategy_analysis(markup_df, eval_df, company_eval, target_units, cfg.out_dir)

    # 11. 保存汇总
    summary = {
        'case_name': cfg.case_name,
        'scenario': scenario_name,
        'target_plants': target_plants or 'all',
        'train_period': f'{cfg.train_start}~{cfg.train_end}',
        'apply_period': f'{cfg.apply_start}~{cfg.apply_end}',
        'n_target_units': len(target_units),
        'n_total_units': len(all_units),
        'n_apply_days': len(data['apply_days']),
        'total_base_revenue': float(company_eval['base_revenue'].sum()),
        'total_strat_revenue': float(company_eval['strat_revenue'].sum()),
        'revenue_change_pct': float((company_eval['strat_revenue'].sum() - company_eval['base_revenue'].sum())
                                   / abs(company_eval['base_revenue'].sum()) * 100),
        'score': float(score),
        'companies': company_eval.to_dict('records'),
        'ensemble_weights_used': 'TCN=0.5, Mamba=0.5 (Step1)',
    }
    with open(os.path.join(cfg.out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ── 完成 ──
    elapsed = time.time() - t0
    pf(f"\n{'=' * 70}")
    pf(f"  Step 2 完成!")
    pf(f"{'=' * 70}")
    pf(f"  耗时: {elapsed:.0f}s")
    pf(f"  理论评分: {score:.1f} 分")
    pf(f"  输出目录: {cfg.out_dir}")
    pf(f"  文件列表:")
    for fn in sorted(os.listdir(cfg.out_dir)):
        fp = os.path.join(cfg.out_dir, fn)
        if os.path.isfile(fp):
            pf(f"    {fn} ({os.path.getsize(fp)/1024:.0f}KB)")
        elif os.path.isdir(fp):
            n = sum(1 for _ in os.walk(fp) for _ in _[2])  # count files
            pf(f"    {fn}/ ({n} files)")
    pf(f"\n  下一步:")
    pf(f"    1. 将 {cfg.out_dir}/modified_input/ 复制到Windows")
    pf(f"    2. 替换原始Input目录中的对应日期文件")
    pf(f"    3. 运行 main_da_market_V1.exe 出清")
    pf(f"    4. 对比Output结果, 运行 Step 4 评价")
    pf(f"\n  ✓ Step 2 完成")


if __name__ == '__main__':
    main()
