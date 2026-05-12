#!/usr/bin/env python3
"""
step4_evaluation.py — 出清后评价 (Step 4)
对比策略出清结果(newoutput) vs 基线出清结果(Output)

运行:
  python step4_evaluation.py                        # 默认: newoutput vs Output
  python step4_evaluation.py --new /path/to/output  # 自定义路径
  python step4_evaluation.py --target G13           # 标注目标电厂
"""
import os, sys, json, csv, argparse
import numpy as np
import openpyxl
from collections import defaultdict

# 自动计算相对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # code/
DELIVERY_DIR = os.path.dirname(SCRIPT_DIR)  # ROTS44_delivery/
PROJECT_ROOT = os.path.dirname(DELIVERY_DIR)  # 项目根目录
CASE_DIR = os.path.join(PROJECT_ROOT, 'Case', 'ROTS 44')  # Case/ROTS 44 (数据源)
OUTPUT_DIR = os.path.join(DELIVERY_DIR, 'ROTS 44')  # ROTS44_delivery/ROTS 44 (输出)

# ═══════════════════════════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(description='出清后评价')
parser.add_argument('--new', default=os.path.join(OUTPUT_DIR, 'clearing_results', 'strategy_output'), help='策略出清结果目录')
parser.add_argument('--old', default=os.path.join(CASE_DIR, 'Output'), help='基线出清结果目录')
parser.add_argument('--out', default=None, help='评价输出目录')
parser.add_argument('--target', default='all', help='目标电厂 (G13/G19/all)')
_args = parser.parse_args()

NEW_OUTPUT = _args.new
OLD_OUTPUT = _args.old
if _args.out:
    OUT_DIR = _args.out
elif _args.target != 'all':
    OUT_DIR = os.path.join(OUTPUT_DIR, 'strategy_output', f'evaluation_{_args.target}')
else:
    OUT_DIR = os.path.join(OUTPUT_DIR, 'strategy_output', 'evaluation')

TARGET_PLANTS = None if _args.target == 'all' else [t.strip() for t in _args.target.split(',')]

SPD = 96  # 96个15分钟时段

# 电厂映射 (从之前提取)
PLANT_MAP = {
    'ThermalPlant_1': 'G13', 'ThermalPlant_2': 'G14',
    'ThermalPlant_3': 'G15', 'ThermalPlant_4': 'G16',
    'ThermalPlant_5': 'G17', 'ThermalPlant_6': 'G18',
    'ThermalPlant_7': 'G19', 'ThermalPlant_8': 'G20',
}

os.makedirs(OUT_DIR, exist_ok=True)


def pf(msg):
    print(msg)


def read_day_output(xlsx_path):
    """读取一天的出清结果"""
    result = {
        'prices': [0]*SPD,
        'plant_revenue': {},   # plant_id → {op_cost, start_cost, bid_qty, bid_avg, bid_rev, net_rev}
        'unit_output': {},     # unit_id → [96 periods of output MW]
        'balance': {},         # name → [96 values]
    }

    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception as e:
        pf(f"    [ERROR] 无法打开 {xlsx_path}: {e}")
        return result

    # 1. 出清电价
    sn_price = 'LevelC_电能量市场出清电价'
    if sn_price in wb.sheetnames:
        ws = wb[sn_price]
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0] == 'Bus_1' and row[1] and '电能量' in str(row[1]):
                result['prices'] = [float(x) if isinstance(x, (int, float)) else 0 for x in row[2:2+SPD]]
                break

    # 2. 火电厂收益
    sn_rev = 'LevelB_火电厂电能量市场收益'
    if sn_rev in wb.sheetnames:
        ws = wb[sn_rev]
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0] and isinstance(row[0], str) and row[0].startswith('ThermalPlant'):
                pid = str(row[0]).strip()
                result['plant_revenue'][pid] = {
                    'plant_name': str(row[1]).strip() if row[1] else pid,
                    'op_cost':    float(row[2]) if isinstance(row[2], (int, float)) else 0,
                    'start_cost': float(row[3]) if isinstance(row[3], (int, float)) else 0,
                    'bid_qty':    float(row[5]) if isinstance(row[5], (int, float)) and len(row) > 5 else 0,
                    'bid_avg':    float(row[6]) if isinstance(row[6], (int, float)) and len(row) > 6 else 0,
                    'bid_rev':    float(row[7]) if isinstance(row[7], (int, float)) and len(row) > 7 else 0,
                    'net_rev':    float(row[8]) if isinstance(row[8], (int, float)) and len(row) > 8 else 0,
                }

    # 3. 机组中标出力
    sn_unit = 'LevelC_机组电能量市场中标结果'
    if sn_unit in wb.sheetnames:
        ws = wb[sn_unit]
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0] and isinstance(row[0], str) and row[0].startswith('Thermal'):
                uid = str(row[0]).strip()
                label = str(row[1]).strip() if row[1] else ''
                if '出力' in label:
                    powers = [float(x) if isinstance(x, (int, float)) else 0 for x in row[2:2+SPD]]
                    result['unit_output'][uid] = powers

    # 4. 电力平衡
    sn_bal = 'LevelC_电力电量平衡表单'
    if sn_bal in wb.sheetnames:
        ws = wb[sn_bal]
        for row in ws.iter_rows(min_row=4, values_only=True):
            name = row[0]
            if name and name in ['火电功率', '风电消纳功率', '光伏消纳功率', '总负荷功率', '库容式水电功率']:
                values = [float(x) if isinstance(x, (int, float)) else 0 for x in row[1:1+SPD]]
                result['balance'][str(name)] = values

    wb.close()
    return result


def main():
    pf("=" * 70)
    pf("  ROTS44 出清后评价 — Step 4")
    pf("  策略出清 vs 基线出清 (14天)")
    pf("=" * 70)

    # 找重叠天数
    new_days = sorted([d for d in os.listdir(NEW_OUTPUT) if d.startswith('2026')])
    old_days = sorted([d for d in os.listdir(OLD_OUTPUT) if d.startswith('2026')])
    overlap = sorted(set(new_days) & set(old_days))
    pf(f"\n  评价天数: {len(overlap)} ({overlap[0]}~{overlap[-1]})")

    # ═══════════════════════════════════════════════════════
    #  读取所有天的数据
    # ═══════════════════════════════════════════════════════
    pf("\n  读取出清结果...")
    all_new = {}
    all_old = {}
    for di, day in enumerate(overlap):
        new_path = os.path.join(NEW_OUTPUT, day, '总体_out.xlsx')
        old_path = os.path.join(OLD_OUTPUT, day, '总体_out.xlsx')
        all_new[day] = read_day_output(new_path)
        all_old[day] = read_day_output(old_path)
        if (di+1) % 5 == 0:
            pf(f"    已处理 {di+1}/{len(overlap)} 天")
    pf(f"    完成, 共 {len(overlap)} 天")

    # ═══════════════════════════════════════════════════════
    #  1. 市场级评价
    # ═══════════════════════════════════════════════════════
    pf("\n" + "=" * 70)
    pf("  ■ 市场级评价")
    pf("=" * 70)

    new_prices_all = []
    old_prices_all = []
    for day in overlap:
        new_prices_all.extend(all_new[day]['prices'])
        old_prices_all.extend(all_old[day]['prices'])

    new_p = np.array(new_prices_all)
    old_p = np.array(old_prices_all)

    pf(f"\n  {'指标':20s} {'基线(BS3)':>12s} {'策略':>12s} {'变化':>12s}")
    pf(f"  {'-'*56}")

    metrics = [
        ('均价(元/MWh)',    np.mean(old_p), np.mean(new_p)),
        ('中位价',          np.median(old_p), np.median(new_p)),
        ('最低价',          np.min(old_p), np.min(new_p)),
        ('最高价',          np.max(old_p), np.max(new_p)),
        ('标准差',          np.std(old_p), np.std(new_p)),
        ('尖峰(>500)占比%', np.mean(old_p > 500)*100, np.mean(new_p > 500)*100),
    ]
    for name, v_old, v_new in metrics:
        delta = v_new - v_old
        pf(f"  {name:20s} {v_old:>12.2f} {v_new:>12.2f} {delta:>+12.2f}")

    # 逐天价格对比
    pf(f"\n  逐天均价对比:")
    pf(f"  {'日期':>10s} {'基线均价':>10s} {'策略均价':>10s} {'变化':>10s} {'变化率':>8s}")
    for day in overlap:
        op = np.mean(all_old[day]['prices'])
        np_ = np.mean(all_new[day]['prices'])
        d = np_ - op
        pct = d / op * 100 if op > 0 else 0
        pf(f"  {day:>10s} {op:>10.2f} {np_:>10.2f} {d:>+10.2f} {pct:>+7.2f}%")

    # ═══════════════════════════════════════════════════════
    #  2. 公司级评价 (核心)
    # ═══════════════════════════════════════════════════════
    pf("\n" + "=" * 70)
    pf("  ■ 公司级评价 (出清后真实收益)")
    pf("=" * 70)

    # 汇总各电厂14天收益
    plant_rev_new = defaultdict(lambda: {'net_rev': 0, 'bid_rev': 0, 'op_cost': 0, 'start_cost': 0, 'bid_qty': 0})
    plant_rev_old = defaultdict(lambda: {'net_rev': 0, 'bid_rev': 0, 'op_cost': 0, 'start_cost': 0, 'bid_qty': 0})

    for day in overlap:
        for pid, rev in all_new[day]['plant_revenue'].items():
            pname = PLANT_MAP.get(pid, pid)
            for k in ['net_rev', 'bid_rev', 'op_cost', 'start_cost', 'bid_qty']:
                plant_rev_new[pname][k] += rev.get(k, 0)

        for pid, rev in all_old[day]['plant_revenue'].items():
            pname = PLANT_MAP.get(pid, pid)
            for k in ['net_rev', 'bid_rev', 'op_cost', 'start_cost', 'bid_qty']:
                plant_rev_old[pname][k] += rev.get(k, 0)

    pf(f"\n  {'公司':6s} {'基线净收益万':>12s} {'策略净收益万':>12s} {'Δ收益万':>10s} {'变化率':>8s} {'基线中标GWh':>12s} {'策略中标GWh':>12s}")
    pf(f"  {'-'*72}")

    total_old = 0
    total_new = 0
    improved = 0
    company_results = []
    target_delta = 0
    rival_delta = 0

    for pname in sorted(set(list(plant_rev_new.keys()) + list(plant_rev_old.keys()))):
        nr_old = plant_rev_old[pname]['net_rev']
        nr_new = plant_rev_new[pname]['net_rev']
        delta = nr_new - nr_old
        pct = delta / abs(nr_old) * 100 if abs(nr_old) > 0.01 else 0
        qty_old = plant_rev_old[pname]['bid_qty'] / 10000  # MWh → GWh
        qty_new = plant_rev_new[pname]['bid_qty'] / 10000

        total_old += nr_old
        total_new += nr_new
        if delta > 0:
            improved += 1

        # 标注目标电厂
        marker = " ★" if (TARGET_PLANTS and pname in TARGET_PLANTS) else ""
        is_target = (TARGET_PLANTS is None) or (pname in TARGET_PLANTS)
        if is_target:
            target_delta += delta
        else:
            rival_delta += delta

        pf(f"  {pname:6s} {nr_old:>12.1f} {nr_new:>12.1f} {delta:>+10.1f} {pct:>+7.2f}% {qty_old:>12.2f} {qty_new:>12.2f}{marker}")

        company_results.append({
            'plant_name': pname,
            'base_net_rev': nr_old,
            'strat_net_rev': nr_new,
            'delta': delta,
            'pct': pct,
            'base_qty': plant_rev_old[pname]['bid_qty'],
            'strat_qty': plant_rev_new[pname]['bid_qty'],
            'is_target': is_target,
        })

    total_delta = total_new - total_old
    total_pct = total_delta / abs(total_old) * 100 if abs(total_old) > 0.01 else 0
    pf(f"  {'-'*72}")
    pf(f"  {'合计':6s} {total_old:>12.1f} {total_new:>12.1f} {total_delta:>+10.1f} {total_pct:>+7.2f}%")
    pf(f"\n  改善公司: {improved}/{len(company_results)}")

    if TARGET_PLANTS:
        pf(f"\n  ▶ 目标电厂({','.join(TARGET_PLANTS)}) 收益变化: {target_delta:>+.1f} 万")
        pf(f"  ▶ 竞争对手收益变化: {rival_delta:>+.1f} 万")
        pf(f"  ▶ 市场总体变化: {total_delta:>+.1f} 万")

    # 公司级详细 (分解: 中标收入/运行成本/启动成本)
    pf(f"\n  收益分解:")
    pf(f"  {'公司':6s} {'基线中标收入':>12s} {'策略中标收入':>12s} {'基线运行成本':>12s} {'策略运行成本':>12s} {'基线启动费':>10s} {'策略启动费':>10s}")
    for pname in sorted(plant_rev_new.keys()):
        o = plant_rev_old[pname]
        n = plant_rev_new[pname]
        pf(f"  {pname:6s} {o['bid_rev']:>12.1f} {n['bid_rev']:>12.1f} {o['op_cost']:>12.1f} {n['op_cost']:>12.1f} {o['start_cost']:>10.1f} {n['start_cost']:>10.1f}")

    # HHI
    total_qty_new = sum(plant_rev_new[p]['bid_qty'] for p in plant_rev_new) or 1
    total_qty_old = sum(plant_rev_old[p]['bid_qty'] for p in plant_rev_old) or 1
    hhi_new = sum((plant_rev_new[p]['bid_qty'] / total_qty_new * 100) ** 2 for p in plant_rev_new)
    hhi_old = sum((plant_rev_old[p]['bid_qty'] / total_qty_old * 100) ** 2 for p in plant_rev_old)
    pf(f"\n  HHI指数: 基线={hhi_old:.0f}, 策略={hhi_new:.0f}, 变化={hhi_new-hhi_old:+.0f}")

    # ═══════════════════════════════════════════════════════
    #  3. 机组级评价
    # ═══════════════════════════════════════════════════════
    pf("\n" + "=" * 70)
    pf("  ■ 机组级评价 (中标出力变化)")
    pf("=" * 70)

    # 汇总机组中标电量
    unit_mwh_new = defaultdict(float)
    unit_mwh_old = defaultdict(float)
    unit_cleared_new = defaultdict(int)  # 中标时段数
    unit_cleared_old = defaultdict(int)

    for day in overlap:
        for uid, powers in all_new[day]['unit_output'].items():
            mwh = sum(p * 0.25 for p in powers)  # 15min → hours, *100 for 100MW
            unit_mwh_new[uid] += mwh * 100  # 100MW单位 → MW
            unit_cleared_new[uid] += sum(1 for p in powers if p > 0.001)

        for uid, powers in all_old[day]['unit_output'].items():
            mwh = sum(p * 0.25 for p in powers)
            unit_mwh_old[uid] += mwh * 100
            unit_cleared_old[uid] += sum(1 for p in powers if p > 0.001)

    pf(f"\n  {'机组':14s} {'基线MWh':>10s} {'策略MWh':>10s} {'Δ MWh':>10s} {'变化率':>8s} {'基线时段':>8s} {'策略时段':>8s}")
    all_uids = sorted(set(list(unit_mwh_new.keys()) + list(unit_mwh_old.keys())),
                       key=lambda x: int(x.split('_')[1]) if '_' in x else 0)

    for uid in all_uids:
        if not uid.startswith('Thermal'):
            continue
        o = unit_mwh_old.get(uid, 0)
        n = unit_mwh_new.get(uid, 0)
        d = n - o
        pct = d / o * 100 if abs(o) > 1 else 0
        co = unit_cleared_old.get(uid, 0)
        cn = unit_cleared_new.get(uid, 0)
        pf(f"  {uid:14s} {o:>10.0f} {n:>10.0f} {d:>+10.0f} {pct:>+7.1f}% {co:>8d} {cn:>8d}")

    # ═══════════════════════════════════════════════════════
    #  4. 评分
    # ═══════════════════════════════════════════════════════
    pf("\n" + "=" * 70)
    pf("  ■ 综合评分")
    pf("=" * 70)

    # 评分维度
    if TARGET_PLANTS:
        # 部分控制: 按目标电厂收益变化评分
        target_base = sum(r['base_net_rev'] for r in company_results if r['is_target'])
        target_strat = sum(r['strat_net_rev'] for r in company_results if r['is_target'])
        target_pct = (target_strat - target_base) / abs(target_base) * 100 if abs(target_base) > 0.01 else 0
        rev_score = max(70, min(100, 70 + target_pct * 2))
        pf(f"\n  目标电厂({','.join(TARGET_PLANTS)}) 收益提升: {target_pct:+.2f}%")
    else:
        target_pct = total_pct
        rev_score = max(70, min(100, 70 + total_pct * 2))

    # 2. 改善公司比例 (附加)
    improve_ratio = improved / max(len(company_results), 1)

    # 3. 市场影响 (出清价变化)
    price_change_pct = (np.mean(new_p) - np.mean(old_p)) / np.mean(old_p) * 100

    pf(f"\n  收益提升: {total_pct:+.2f}% → 收益评分: {rev_score:.1f}")
    pf(f"  改善公司: {improved}/{len(company_results)} ({improve_ratio*100:.0f}%)")
    pf(f"  出清均价变化: {price_change_pct:+.2f}%")
    pf(f"  HHI变化: {hhi_new-hhi_old:+.0f}")
    pf(f"\n  ★ 综合评分: {rev_score:.1f} 分")

    # ═══════════════════════════════════════════════════════
    #  5. 保存结果
    # ═══════════════════════════════════════════════════════
    # CSV: 公司级
    csv_path = os.path.join(OUT_DIR, 'post_clearing_company.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['plant_name','base_net_rev','strat_net_rev','delta','pct','base_qty','strat_qty','is_target'])
        w.writeheader()
        w.writerows(company_results)

    # CSV: 逐天价格
    csv_path2 = os.path.join(OUT_DIR, 'post_clearing_daily_prices.csv')
    with open(csv_path2, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['day','base_mean_price','strat_mean_price','delta','pct'])
        for day in overlap:
            op = np.mean(all_old[day]['prices'])
            np_ = np.mean(all_new[day]['prices'])
            d = np_ - op
            pct = d / op * 100 if op > 0 else 0
            w.writerow([day, f'{op:.2f}', f'{np_:.2f}', f'{d:.2f}', f'{pct:.2f}'])

    # JSON: 汇总
    summary = {
        'n_days': len(overlap),
        'date_range': f'{overlap[0]}~{overlap[-1]}',
        'target_plants': TARGET_PLANTS or 'all',
        'total_base_revenue': total_old,
        'total_strat_revenue': total_new,
        'revenue_delta': total_delta,
        'revenue_pct': total_pct,
        'target_delta': target_delta if TARGET_PLANTS else total_delta,
        'rival_delta': rival_delta if TARGET_PLANTS else 0,
        'improved_companies': improved,
        'total_companies': len(company_results),
        'base_mean_price': float(np.mean(old_p)),
        'strat_mean_price': float(np.mean(new_p)),
        'price_change_pct': price_change_pct,
        'hhi_base': hhi_old,
        'hhi_strat': hhi_new,
        'score': rev_score,
        'companies': company_results,
    }
    json_path = os.path.join(OUT_DIR, 'post_clearing_summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    pf(f"\n  结果保存至: {OUT_DIR}")
    pf(f"    post_clearing_company.csv")
    pf(f"    post_clearing_daily_prices.csv")
    pf(f"    post_clearing_summary.json")
    pf(f"\n  ✓ Step 4 评价完成")


if __name__ == '__main__':
    main()
