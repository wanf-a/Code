"""策略报价分析服务"""
import json, os
import pandas as pd

DELIVERY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'market', 'ROTS44_delivery', 'ROTS 44')

def _find_dir():
    if os.path.isdir(DELIVERY_DIR):
        return DELIVERY_DIR
    return None

def get_company_strategy_detail(plant_name):
    base = _find_dir()
    if not base: return None
    out_dir = os.path.join(base, f'strategy_output_{plant_name}')
    if not os.path.isdir(out_dir): return None
    result = {'plant_name': plant_name}
    sp = os.path.join(out_dir, 'summary.json')
    if os.path.exists(sp):
        with open(sp, 'r', encoding='utf-8') as f: result['summary'] = json.load(f)
    mp = os.path.join(out_dir, 'strategy_markups.csv')
    if os.path.exists(mp):
        df = pd.read_csv(mp)
        daily = df.groupby('day').agg({'alpha_phys':'mean','alpha_pred':'mean','markup':'mean','sec1_price':'mean','bs3_sec1':'mean','sdr':'first','pred_spike':'first'}).reset_index()
        result['daily_markups'] = daily.to_dict('records')
    ep = os.path.join(out_dir, 'evaluation_company.csv')
    if os.path.exists(ep):
        result['evaluation_company'] = pd.read_csv(ep).to_dict('records')
    pp = os.path.join(base, 'strategy_output', f'evaluation_{plant_name}', 'post_clearing_summary.json')
    if os.path.exists(pp):
        with open(pp, 'r', encoding='utf-8') as f: result['post_clearing'] = json.load(f)
    return result
