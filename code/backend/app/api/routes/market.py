"""电力市场平台 API"""
from __future__ import annotations
from datetime import datetime, timedelta, date as date_type
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import AdminUser
from app.api.deps import get_current_admin
from app.db.session import SessionLocal
from app.db.deps import get_db
from app.models.market import (
    MarketThermalPlant,
    MarketThermalUnit,
    MarketWindUnit,
    MarketSolarUnit,
    MarketClearingHistory,
    MarketOutResult,
    MarketDayAheadQuote,
    MarketLoad,
    InputDayAheadUnitQuote,
    OutputEnergyMarketOverview,
    OutputThermalPlantRevenue
)
from app.models.price_prediction import PricePrediction
from app.models.output_power_balance import OutputPowerBalanceSheet, OutputUnitBidResults
from app.services.power_balance_service import PowerBalanceService

router = APIRouter()


class InputDayAheadQuoteSegment(BaseModel):
    start: float
    end: float
    price: float
    quote_time: int | None = None
    quote_section: str | None = None
    market_name: str | None = None


class InputDayAheadQuoteSubmit(BaseModel):
    unit_id: str
    data_date: str
    use_default_case: bool = False
    segments: list[InputDayAheadQuoteSegment]


# ==================== 企业信息 ====================

@router.get("/companies")
def get_companies(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取火电厂列表及其机组"""
    plants = db.query(MarketThermalPlant).order_by(MarketThermalPlant.id).all()
    result = []
    for p in plants:
        units = db.query(MarketThermalUnit).filter(
            MarketThermalUnit.plant_id == p.plant_id
        ).order_by(MarketThermalUnit.id).all()
        result.append({
            "id": p.plant_id,
            "name": p.name,
            "units": [
                {
                    "id": u.unit_id,
                    "bus": u.bus_id,
                    "capacity": u.capacity,
                    "initState": "TRUE" if u.initial_state else "FALSE",
                    "initDuration": u.initial_duration,
                    "minOutput": u.min_output,
                    "rampUp": u.ramp_up,
                    "rampDown": u.ramp_down,
                    "minOnTime": u.min_on_time,
                    "minOffTime": u.min_off_time,
                    "startCost": u.start_cost,
                    "stopCost": u.stop_cost,
                    "fuel": u.fuel_id,
                    "costA": u.cost_a,
                    "costB": u.cost_b,
                    "costC": u.cost_c,
                    "freqResp": round(u.freq_response, 6),
                    "freqErr": round(u.freq_error, 6),
                    "regSpeed": round(u.reg_speed, 6),
                }
                for u in units
            ],
        })
    return {"items": result}


@router.get("/wind-units")
def get_wind_units(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取风电场列表"""
    units = db.query(MarketWindUnit).order_by(MarketWindUnit.id).all()
    return {
        "items": [
            {
                "id": u.id,
                "name": u.name,
                "bus": u.bus_id,
                "capacity": u.capacity,
                "power_factor": u.power_factor,
            }
            for u in units
        ]
    }


@router.get("/solar-units")
def get_solar_units(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取光伏电站列表"""
    units = db.query(MarketSolarUnit).order_by(MarketSolarUnit.id).all()
    return {
        "items": [
            {
                "id": u.id,
                "name": u.name,
                "bus": u.bus_id,
                "capacity": u.capacity,
                "power_factor": u.power_factor,
            }
            for u in units
        ]
    }


# ==================== 电价预测 ====================

@router.get("/price-predictions")
def get_price_predictions(
    day: int = Query(..., description="天数，1-7"),
    model: str = Query(..., description="预测模型名称"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """获取电价预测数据"""
    try:
        # 根据 day 计算对应的日期
        # 第一天对应 2026-01-01（数据库实际起始日期），第二天对应 2026-01-02，以此类推
        base_date = "2026-03-19"
        # 计算目标日期
        date_obj = datetime.strptime(base_date, "%Y-%m-%d")
        target_date_obj = date_obj + timedelta(days=day-1)
        target_day = target_date_obj.strftime("%Y-%m-%d")
        
        # 查询该日期的所有时段数据
        predictions = db.query(PricePrediction).filter(
            PricePrediction.day == target_day
        ).all()
        
        # 按时段排序（确保 96 个时段按顺序返回）
        predictions.sort(key=lambda x: x.period)
        
        # 提取指定模型的预测值
        values = []
        q05_values = []  # 95%概率区间下限
        q95_values = []  # 95%概率区间上限
        
        for pred in predictions:
            if model == "true":
                values.append(pred.true_price)
                q05_values.append(pred.true_price)  # 实际价格没有区间
                q95_values.append(pred.true_price)
            elif model == "mamba":
                values.append(pred.Mamba_q0_5)
                q05_values.append(pred.Mamba_q0_05 if hasattr(pred, 'Mamba_q0_05') else pred.Mamba_q0_5)
                q95_values.append(pred.Mamba_q0_95 if hasattr(pred, 'Mamba_q0_95') else pred.Mamba_q0_5)
            elif model == "tcn":
                values.append(pred.TCN_q0_5)
                q05_values.append(pred.TCN_q0_05 if hasattr(pred, 'TCN_q0_05') else pred.TCN_q0_5)
                q95_values.append(pred.TCN_q0_95 if hasattr(pred, 'TCN_q0_95') else pred.TCN_q0_5)
            elif model == "ensemble":
                values.append(pred.Ensemble_q0_5)
                q05_values.append(pred.Ensemble_q0_05 if hasattr(pred, 'Ensemble_q0_05') else pred.Ensemble_q0_5)
                q95_values.append(pred.Ensemble_q0_95 if hasattr(pred, 'Ensemble_q0_95') else pred.Ensemble_q0_5)
            elif model == "naive":
                values.append(pred.NLinear_q0_5)
                q05_values.append(pred.NLinear_q0_5)
                q95_values.append(pred.NLinear_q0_5)
            else:
                # 默认返回实际价格
                values.append(pred.true_price)
                q05_values.append(pred.true_price)
                q95_values.append(pred.true_price)
        
        return {"items": [{"values": values, "q05_values": q05_values, "q95_values": q95_values}]}
    except Exception as e:
        # 返回空数组但保持正确的响应格式
        print(f"获取电价预测数据失败：{e}")
        import traceback
        traceback.print_exc()
        return {"items": [{"values": [], "q05_values": [], "q95_values": []}]}


# ==================== 市场交易 ====================

@router.get("/day-ahead-quotes")
def get_day_ahead_quotes(
    unit_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取日前市场报价"""
    query = db.query(MarketDayAheadQuote)
    if unit_id:
        query = query.filter(MarketDayAheadQuote.unit_id == unit_id)
    quotes = query.order_by(MarketDayAheadQuote.quote_id).all()
    return {
        "items": [
            {
                "quote_id": q.quote_id,
                "unit_id": q.unit_id,
                "market_name": q.market_name,
                "quote_time": q.quote_time,
                "quote_section": q.quote_section,
                "quote_price": q.quote_price,
                "quote_quantity": q.quote_quantity,
                "is_used": q.is_used,
            }
            for q in quotes
        ]
    }


@router.get("/input-day-ahead-quotes")
def get_input_day_ahead_quotes(
    unit_id: Optional[str] = None,
    data_date: Optional[str] = None,
    use_default_case: bool = False,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取输入日前市场报价
    根据用户名动态确定 case_id：用户名 G15 -> case_id Input15
    当 use_default_case 为 True 时，使用默认 case_id Input0
    """
    # 确定 case_id
    if use_default_case:
        # 未点击策略报价按钮时，使用默认 case_id Input0
        case_id = "Input0"
    else:
        # 点击策略报价按钮后，根据用户名生成 case_id
        username = current_admin.username
        import re
        match = re.search(r'\d+', username)
        if match:
            num = match.group()
            case_id = f"Input{num}"
        else:
            # 如果没有数字，默认使用 Input0
            case_id = "Input0"
    
    # 记录调试信息
    print(f"[DEBUG] 查询条件：unit_id={unit_id}, data_date={data_date}, case_id={case_id}, username={current_admin.username}")
    
    # 构建查询
    query = db.query(InputDayAheadUnitQuote)
    
    # 首先尝试使用指定的 case_id 查询
    if case_id:
        query = query.filter(InputDayAheadUnitQuote.case_id == case_id)
    if unit_id:
        query = query.filter(InputDayAheadUnitQuote.UnitId == unit_id)
    if data_date:
        query = query.filter(InputDayAheadUnitQuote.data_date == data_date)
    
    # 执行查询
    quotes = query.order_by(
        InputDayAheadUnitQuote.QuoteTime,
        InputDayAheadUnitQuote.QuoteSection
    ).all()
    
    # 记录查询结果数量
    print(f"[DEBUG] 查询结果数量：{len(quotes)}")
    
    # 如果查询结果为空，尝试使用 Input0 case_id 查询
    if not quotes:
        print(f"[WARNING] 未找到数据，尝试使用 Input0 case_id 查询...")
        query = db.query(InputDayAheadUnitQuote)
        query = query.filter(InputDayAheadUnitQuote.case_id == "Input0")
        if unit_id:
            query = query.filter(InputDayAheadUnitQuote.UnitId == unit_id)
        if data_date:
            query = query.filter(InputDayAheadUnitQuote.data_date == data_date)
        
        quotes = query.order_by(
            InputDayAheadUnitQuote.QuoteTime,
            InputDayAheadUnitQuote.QuoteSection
        ).all()
        
        print(f"[DEBUG] 使用 Input0 case_id 查询结果数量：{len(quotes)}")
    
    # 如果仍然为空，记录详细信息以便调试
    if not quotes:
        print(f"[WARNING] 仍然未找到数据，尝试诊断问题...")
        # 检查该日期是否有其他 case_id 的数据
        if data_date:
            available_cases = db.query(InputDayAheadUnitQuote.case_id).filter(
                InputDayAheadUnitQuote.data_date == data_date
            ).distinct().all()
            print(f"[DEBUG] 该日期可用的 case_id: {[c[0] for c in available_cases]}")
        
        # 检查该机组是否有数据
        if data_date:
            available_units = db.query(InputDayAheadUnitQuote.UnitId).filter(
                InputDayAheadUnitQuote.data_date == data_date
            ).distinct().all()
            print(f"[DEBUG] 该日期可用的机组：{[u[0] for u in available_units]}")
        
        # 检查是否有任何数据
        total_count = db.query(InputDayAheadUnitQuote).count()
        print(f"[DEBUG] 表中总数据量：{total_count}")
    
    return {
        "items": [
            {
                "quote_id": q.QuoteId,
                "unit_id": q.UnitId,
                "market_name": q.MarketName,
                "quote_time": q.QuoteTime,
                "quote_section": q.QuoteSection,
                "quote_price": q.QuotePrice,
                "quote_capacity": q.QuoteCapacity,
                "is_used": q.IsUsed,
                "case_id": q.case_id,
                "data_date": q.data_date,
            }
            for q in quotes
        ]
    }


@router.post("/input-day-ahead-quotes")
def submit_input_day_ahead_quotes(
    payload: InputDayAheadQuoteSubmit,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """提交输入日前市场报价（写入数据库）"""
    # 确定 case_id
    if payload.use_default_case:
        case_id = "Input0"
    else:
        username = current_admin.username
        import re
        match = re.search(r'\d+', username)
        if match:
            num = match.group()
            case_id = f"Input{num}"
        else:
            case_id = "Input0"

    if not payload.segments:
        return {"ok": False, "detail": "no segments"}

    # 清理同一日期、同一机组、同一 case 的旧数据
    db.query(InputDayAheadUnitQuote).filter(
        InputDayAheadUnitQuote.case_id == case_id,
        InputDayAheadUnitQuote.UnitId == payload.unit_id,
        InputDayAheadUnitQuote.data_date == payload.data_date,
    ).delete(synchronize_session=False)

    # 生成新的 QuoteId
    max_id = db.query(func.max(InputDayAheadUnitQuote.QuoteId)).scalar() or 0
    next_id = int(max_id)

    rows = []
    for idx, seg in enumerate(payload.segments, start=1):
        next_id += 1
        quote_time = seg.quote_time if seg.quote_time is not None else idx
        quote_section = seg.quote_section or f"Q{idx}"
        market_name = seg.market_name or "电能量市场申报"
        capacity = max(0.0, float(seg.end) - float(seg.start))
        rows.append(
            InputDayAheadUnitQuote(
                QuoteId=next_id,
                UnitId=payload.unit_id,
                MarketName=market_name,
                QuoteTime=int(quote_time),
                QuoteSection=quote_section,
                QuotePrice=float(seg.price),
                QuoteCapacity=capacity,
                IsUsed=True,
                case_id=case_id,
                data_date=payload.data_date,
            )
        )

    db.add_all(rows)
    db.commit()
    return {"ok": True, "case_id": case_id, "count": len(rows)}


# ==================== 出清结果 ====================

@router.get("/out-results")
def get_out_results(
    sheet: str = Query(..., description="工作表名称"),
    row_index: Optional[int] = Query(None, description="行索引"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取市场出清结果"""
    query = db.query(MarketOutResult).filter(
        MarketOutResult.sheet_name == sheet
    )
    
    if row_index is not None:
        query = query.filter(MarketOutResult.row_index == row_index)
    
    results = query.order_by(
        MarketOutResult.row_index
    ).all()
    
    # 转换为前端需要的格式
    # 每条记录的 period_values 就是一个包含 96 个时段的数组
    items = []
    for r in results:
        # period_values 是 JSON 类型，已经是列表
        values = r.period_values if r.period_values else []
        # 确保值是浮点数类型
        values = [float(v) if v is not None else 0.0 for v in values]
        
        items.append({
            "row_index": r.row_index,
            "values": values
        })
    
    return {"items": items}


# ==================== 电能量市场出清电价 ====================

from app.models.market import OutputClearingPrice, MarketThermalUnit

@router.get("/clearing-price")
def get_clearing_price(
    unit_id: str = Query(..., description="机组 ID，如 Thermal_1"),
    day_index: int = Query(1, description="第几天，从 1 开始（第一天=20260319）"),
    use_default_case: bool = Query(False, description="是否使用默认案例 Output0（基线申报），false 则使用用户关联案例（自主申报）"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取电能量市场出清电价数据
    
    支持根据登录用户名和日期动态获取对应的出清电价数据
    - 自主申报：use_default_case=false，根据用户名生成 case_id（如 G14->Output14）
    - 基线申报：use_default_case=true，固定使用 Output0
    
    :param unit_id: 机组 ID，用于查找所属母线
    :param day_index: 第几天，从 1 开始计数，第一天为 20260319
    :param use_default_case: 是否使用默认案例 Output0
                           - true: 使用 Output0（基线申报）
                           - false: 使用用户名关联的 case_id（自主申报，如 G14->Output14）
    :return: 包含 bus_id, price_type, t1-t96, case_id, date_str 的数据对象
    """
    try:
        # 基础日期
        base_date_str = "20260319"
        
        # 计算实际日期（day_index 从 1 开始，所以偏移量为 day_index - 1）
        day_offset = day_index - 1
        
        # 获取当前用户名
        username = current_admin.username
        
        # 根据参数决定使用的 case_id
        if use_default_case:
            # 基线申报：固定使用 Output0
            case_id = "Output0"
        else:
            # 自主申报：根据用户名生成 case_id（如 G14 -> Output14）
            # 提取用户名中的数字部分
            import re
            match = re.search(r'\d+', username)
            if match:
                case_num = match.group()
                case_id = f"Output{case_num}"
            else:
                # 如果用户名中没有数字，降级处理使用 Output0
                print(f"[出清电价 API] 警告：用户名 {username} 中没有数字，使用 Output0")
                case_id = "Output0"
        
        # 计算查询日期
        from datetime import timedelta
        base_date = datetime.strptime(base_date_str, "%Y%m%d")
        query_date = base_date + timedelta(days=day_offset)
        query_date_str = query_date.strftime("%Y%m%d")
        
        print(f"\n[出清电价 API] 请求参数:")
        print(f"  unit_id: {unit_id}")
        print(f"  day_index: {day_index}")
        print(f"  use_default_case: {use_default_case}")
        print(f"  username: {username}")
        print(f"  生成的 case_id: {case_id}")
        print(f"  查询的日期：{query_date_str}")
        
        # 查询机组信息，获取 bus_id
        unit = db.query(MarketThermalUnit).filter(
            MarketThermalUnit.unit_id == unit_id
        ).first()
        
        if not unit:
            print(f"[出清电价 API] 错误：未找到机组 {unit_id}")
            return {
                "items": [],
                "case_id": case_id,
                "date_str": query_date_str
            }
        
        bus_id = unit.bus_id
        print(f"  机组 {unit_id} 的 bus_id: {bus_id}")
        
        # 导入 OutputClearingPrice 模型
        from app.models.market import OutputClearingPrice
        
        # 查询出清价格数据
        clearing_price_record = db.query(OutputClearingPrice).filter(
            OutputClearingPrice.case_id == case_id,
            OutputClearingPrice.date_str == query_date_str,
            OutputClearingPrice.bus_id == bus_id,
            OutputClearingPrice.price_type == "电能量电价"
        ).first()
        
        if not clearing_price_record:
            print(f"[出清电价 API] 警告：未找到数据 - case_id={case_id}, date={query_date_str}, bus={bus_id}")
            return {
                "items": [],
                "case_id": case_id,
                "date_str": query_date_str
            }
        
        # 构建返回数据
        item = {
            "bus_id": clearing_price_record.bus_id,
            "price_type": clearing_price_record.price_type,
            "case_id": clearing_price_record.case_id,
            "date_str": clearing_price_record.date_str,
            "values": [
                getattr(clearing_price_record, f't{i}', None) 
                for i in range(1, 97)
            ]
        }
        
        print(f"[出清电价 API] 成功获取数据，共 {len([v for v in item['values'] if v is not None])} 个有效数据点")
        
        return {
            "items": [item],
            "case_id": case_id,
            "date_str": query_date_str
        }
    
    except Exception as e:
        print(f"[出清电价 API] 获取数据失败：{e}")
        import traceback
        traceback.print_exc()
        return {
            "items": [],
            "case_id": "Output0",
            "date_str": ""
        }


# ==================== 结算报告 ====================

@router.get("/settlement-overview")
def get_settlement_overview(
    day_index: int = 1,  # 第几天，从 1 开始
    use_default_case: bool = False,  # 是否使用默认案例 Output0
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    """获取结算概览数据（支持日期切换和案例选择）"""
    try:
        print("=" * 80)
        print("【调试信息】/api/market/settlement-overview")
        
        username = current_user.username
        print(f"当前用户对象：{current_user}")
        print(f"当前用户名：{username}")
        print(f"当前用户 email: {getattr(current_user, 'email', 'N/A')}")
        
        # 根据 use_default_case 参数决定使用哪个 case_id
        if use_default_case:
            case_id = "Output0"
            print(f"使用默认案例：{case_id} (基线申报)")
        else:
            # 从用户名中提取数字部分，如 G13 -> 13, admin -> 0
            import re
            match = re.search(r'\d+', username)
            if match:
                num = match.group()
                case_id = f"Output{num}"
            else:
                case_id = "Output0"
            print(f"使用用户关联案例：{case_id} (自主申报)")
        
        # 根据第几天计算实际日期（第一天=20260319）
        from datetime import datetime, timedelta
        base_date = datetime(2026, 3, 19)  # 起始日期
        target_date = base_date + timedelta(days=day_index - 1)
        date_str = target_date.strftime("%Y%m%d")
        print(f"请求的日期索引：第 {day_index} 天")
        print(f"计算得到的日期：{date_str}")
        
        # 先查询该 case_id 下有哪些日期
        from sqlalchemy import distinct
        available_dates = db.query(distinct(OutputEnergyMarketOverview.date_str)).filter(
            OutputEnergyMarketOverview.case_id == case_id
        ).all()
        available_dates_list = [d[0] for d in available_dates]
        print(f"数据库中 {case_id} 的可用日期：{available_dates_list}")
        
        # 检查计算的日期是否在数据库中存在
        if date_str not in available_dates_list:
            print(f"⚠️ 警告：计算日期 {date_str} 不在数据库中")
            # 如果不存在，使用最接近的可用日期
            valid_dates = [d for d in available_dates_list if d >= date_str]
            if valid_dates:
                date_str = min(valid_dates)
                print(f"使用之后的第一个可用日期：{date_str}")
            elif available_dates_list:
                date_str = max(available_dates_list)
                print(f"没有之后的日期，使用最新日期：{date_str}")
        
        # 查询指定日期的所有记录
        records = db.query(OutputEnergyMarketOverview).filter(
            OutputEnergyMarketOverview.case_id == case_id,
            OutputEnergyMarketOverview.date_str == date_str
        ).all()
        
        if records and len(records) > 0:
            print(f"成功找到日期 {date_str} 的数据，共 {len(records)} 条记录")
        else:
            print(f"警告：case_id '{case_id}' 在日期 {date_str} 没有找到数据")
            return {"energy_market": {}}
        
        # 将行转列数据转换为字典
        data_dict = {}
        for record in records:
            key = record.market_name
            value = record.spot_market
            data_dict[key] = value
            print(f"  [{key}] = {value}")
        
        print(f"data_dict 共有 {len(data_dict)} 个字段")
        
        # 构造返回数据结构
        overview_data = {
            "energy_market": {}
        }
        
        if data_dict:
            # 将中文键名转换为英文键名，以匹配前端期望的格式
            overview_data["energy_market"] = {
                "avg_price": data_dict.get("成交均价(元/MWh)", 0) if data_dict.get("成交均价(元/MWh)") is not None else 0.0,
                "max_node_price": data_dict.get("最高节点电价(元/MWh)", 0) if data_dict.get("最高节点电价(元/MWh)") is not None else 0.0,
                "min_node_price": data_dict.get("最低节点电价(元/MWh)", 0) if data_dict.get("最低节点电价(元/MWh)") is not None else 0.0,
                "avg_quote_price": data_dict.get("申报均价(元/MWh)", 0) if data_dict.get("申报均价(元/MWh)") is not None else 0.0,
                "supply_demand_ratio": data_dict.get("供需比", 0) if data_dict.get("供需比") is not None else 0.0,
                "total_generation": data_dict.get("总发电量(100MWh)", 0) * 100 if data_dict.get("总发电量(100MWh)") is not None else 0.0,
                "total_consumption": data_dict.get("总用电量(100MWh)", 0) * 100 if data_dict.get("总用电量(100MWh)") is not None else 0.0,
                "re_curtailment": data_dict.get("新能源总弃电量(100MWh)", 0) * 100 if data_dict.get("新能源总弃电量(100MWh)") is not None else 0.0,
                "quote_quantity": data_dict.get("申报出力(MW)", 0) if data_dict.get("申报出力(MW)") is not None else 0.0,
                "total_output": data_dict.get("成交总出力(100MW)", 0) if data_dict.get("成交总出力(100MW)") is not None else 0.0,
                "total_capacity": data_dict.get("总装机容量(100MW)", 0) if data_dict.get("总装机容量(100MW)") is not None else 0.0,
                "plant_count": int(data_dict.get("发电企业数目", 0)) if data_dict.get("发电企业数目") is not None else 0,
                "quote_unit_count": int(data_dict.get("申报机组数目", 0)) if data_dict.get("申报机组数目") is not None else 0,
                "bid_units": int(data_dict.get("中标机组数目", 0)) if data_dict.get("中标机组数目") is not None else 0,
                "total_revenue": data_dict.get("总交易额(万元)", 0) if data_dict.get("总交易额(万元)") is not None else 0.0,
                "wind_count": int(data_dict.get("风电数", 0)) if data_dict.get("风电数") is not None else 0,
                "solar_count": int(data_dict.get("光伏数", 0)) if data_dict.get("光伏数") is not None else 0,
                "hydro_count": int(data_dict.get("水电数", 0)) if data_dict.get("水电数") is not None else 0,
                "thermal_count": int(data_dict.get("火电数", 0)) if data_dict.get("火电数") is not None else 0,
                "battery_count": int(data_dict.get("电化学储能数", 0)) if data_dict.get("电化学储能数") is not None else 0,
                "pumped_count": int(data_dict.get("抽蓄电站数", 0)) if data_dict.get("抽蓄电站数") is not None else 0,
                "wind_capacity": data_dict.get("风电装机容量(100MW)", 0) if data_dict.get("风电装机容量(100MW)") is not None else 0.0,
                "solar_capacity": data_dict.get("光伏装机容量(100MW)", 0) if data_dict.get("光伏装机容量(100MW)") is not None else 0.0,
                "hydro_capacity": data_dict.get("水电装机容量(100MW)", 0) if data_dict.get("水电装机容量(100MW)") is not None else 0.0,
                "thermal_capacity": data_dict.get("火电装机容量(100MW)", 0) if data_dict.get("火电装机容量(100MW)") is not None else 0.0,
                "congestion_status": data_dict.get("阻塞情况", "无"),
                "congestion_surplus": data_dict.get("阻塞盈余(万元)", 0) if data_dict.get("阻塞盈余(万元)") is not None else 0.0,
            }
            
            print("\n返回前端的数据:")
            for k, v in overview_data["energy_market"].items():
                print(f"  {k}: {v}")
        
        print("=" * 80)
        
        return overview_data
    except Exception as e:
        print(f"获取结算概览失败：{e}")
        import traceback
        traceback.print_exc()
        return {"energy_market": {}}
    finally:
        # 确保数据库会话被关闭
        if 'db' in locals():
            db.close()


@router.get("/settlement-detail")
def get_settlement_detail(
    day_index: int = 1,  # 第几天，从 1 开始
    use_default_case: bool = False,  # 是否使用默认案例 Output0
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取结算明细（支持日期切换和案例选择）"""
    try:
        # 获取当前用户的 case_id
        username = _admin.username
        
        # 根据 use_default_case 参数决定使用哪个 case_id
        if use_default_case:
            case_id = "Output0"
            print(f"使用默认案例：{case_id} (基线申报)")
        else:
            # 从用户名中提取数字部分，如 G13 -> 13, admin -> 0
            import re
            match = re.search(r'\d+', username)
            if match:
                num = match.group()
                case_id = f"Output{num}"
            else:
                case_id = "Output0"
            print(f"使用用户关联案例：{case_id} (自主申报)")
        
        # 根据第几天计算实际日期（第一天=20260319）
        from datetime import datetime, timedelta
        base_date = datetime(2026, 3, 19)  # 起始日期
        target_date = base_date + timedelta(days=day_index - 1)
        date_str = target_date.strftime("%Y%m%d")
        print(f"请求的日期索引：第 {day_index} 天")
        print(f"计算得到的日期：{date_str}")
        
        # 查询该 case_id 和 date_str 下的所有数据
        results = db.query(OutputThermalPlantRevenue).filter(
            OutputThermalPlantRevenue.case_id == case_id,
            OutputThermalPlantRevenue.date_str == date_str
        ).all()
        
        if not results:
            print(f"警告：case_id '{case_id}' 在日期 {date_str} 没有找到数据")
            print("尝试使用 Output0 作为默认 case_id...")
            case_id = "Output0"
            results = db.query(OutputThermalPlantRevenue).filter(
                OutputThermalPlantRevenue.case_id == case_id,
                OutputThermalPlantRevenue.date_str == date_str
            ).all()
        
        if not results:
            print(f"错误：默认 case_id '{case_id}' 也没有数据")
            return {"energy_rows": []}
        
        # 转换为前端需要的格式
        energy_rows = []
        for r in results:
            # 将字符串转换为浮点数，处理 None 值
            def to_float(val):
                if val is None:
                    return 0.0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0
            
            energy_rows.append({
                "id": r.unit_id or r.name or "",
                "name": r.name or "",
                "opCost": to_float(r.operation_cost),
                "startCost": to_float(r.open_cost),
                "stopCost": float(r.close_cost) if r.close_cost else 0.0,
                "output": to_float(r.bid_quantity),
                "avgPrice": to_float(r.bid_average_price),
                "revenue": to_float(r.bid_revenue),
                "netIncome": to_float(r.net_revenue),
            })
        
        return {"energy_rows": energy_rows}
    except Exception as e:
        print(f"获取结算明细失败：{e}")
        import traceback
        traceback.print_exc()
        return {"energy_rows": []}


@router.get("/balance-chart")
def get_balance_chart(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取收支平衡图数据"""
    # TODO: 实现收支平衡图逻辑
    return {"items": []}


# ==================== 历史出清 ====================

@router.get("/clearing-history")
def get_clearing_history(
    metric: str = Query("price", description="指标类型：price, load, wind, solar"),
    start: int = Query(0, description="起始索引"),
    limit: int = Query(100, description="数量限制"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取历史出清数据"""
    query = db.query(MarketClearingHistory)
    
    # 根据指标类型过滤
    if metric == "price":
        query = query.filter(MarketClearingHistory.metric_name.like("%电价%"))
    elif metric == "load":
        query = query.filter(MarketClearingHistory.metric_name.like("%负荷%"))
    elif metric == "wind":
        query = query.filter(MarketClearingHistory.metric_name.like("%风电%"))
    elif metric == "solar":
        query = query.filter(MarketClearingHistory.metric_name.like("%光伏%"))
    
    # 排序并分页
    results = query.order_by(
        MarketClearingHistory.record_time.desc()
    ).offset(start).limit(limit).all()
    
    return {
        "items": [
            {
                "id": r.id,
                "metric_name": r.metric_name,
                "value": float(r.value) if r.value else 0,
                "record_time": r.record_time.isoformat() if r.record_time else None,
            }
            for r in results
        ]
    }


@router.get("/power-balance")
def get_power_balance(
    date_str: str = Query(..., description="日期字符串，如 20260319"),
    case_id: Optional[str] = Query(None, description="案例 ID，如 Output1，默认为当前用户的 case"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取信息披露页面的功率平衡数据
    根据用户名和日期查询对应的风电、光伏、负荷预测数据
    用户名与 case_id 的对应关系：用户名 G13 -> case_id Output13
    """
    try:
        # 如果未传入 case_id，根据用户名生成
        if not case_id:
            username = current_admin.username
            # 提取用户名中的数字部分
            import re
            match = re.search(r'\d+', username)
            if match:
                num = match.group()
                case_id = f"Output{num}"
            else:
                # 如果没有数字，默认使用 Output0
                case_id = "Output0"
        
        # 查询该日期和 case_id 的所有数据
        query = db.query(OutputPowerBalanceSheet).filter(
            OutputPowerBalanceSheet.date_str == date_str,
            OutputPowerBalanceSheet.case_id == case_id
        )
        
        results = query.order_by(OutputPowerBalanceSheet.name).all()
        
        # 转换为前端需要的格式
        items = []
        for r in results:
            # 使用 period_values 属性获取 t1-t96 的值
            values = r.period_values
            # 确保值是浮点数类型，处理 None 值
            values = [float(v) if v is not None else 0.0 for v in values]
            
            items.append({
                "name": r.name,
                "values": values
            })
        
        return {
            "items": items,
            "case_id": case_id,
            "date_str": date_str
        }
    
    except Exception as e:
        print(f"获取功率平衡数据失败：{e}")
        import traceback
        traceback.print_exc()
        return {
            "items": [],
            "case_id": "",
            "date_str": ""
        }


# ==================== 自主申报 - 电力电量平衡结果 ====================

@router.get("/energy-balance")
def get_energy_balance(
    day_index: int = Query(1, description="第几天，从 1 开始（第一天=20260319）"),
    use_default_case: bool = Query(False, description="是否使用默认案例 Output0（基线申报），false 则使用用户关联案例（自主申报）"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取电力电量平衡结果图表数据
    
    支持根据登录用户名和日期动态获取对应的火电、风电、光伏、水电、总负荷数据
    - 自主申报：use_default_case=false，根据用户名生成 case_id（如 G14->Output14）
    - 基线申报：use_default_case=true，固定使用 Output0
    
    :param day_index: 第几天，从 1 开始计数，第一天为 20260319
    :param use_default_case: 是否使用默认案例 Output0
                           - true: 使用 Output0（基线申报）
                           - false: 使用用户名关联的 case_id（自主申报，如 G14->Output14）
    :return: 包含 thermal, wind, solar, hydro, load 数组的数据对象
    """
    try:
        service = PowerBalanceService()
        
        # 基础日期
        base_date_str = "20260319"
        
        # 计算实际日期（day_index 从 1 开始，所以偏移量为 day_index - 1）
        day_offset = day_index - 1
        
        # 获取当前用户名
        username = current_admin.username
        
        # 根据参数决定使用的 case_id
        if use_default_case:
            # 基线申报：固定使用 Output0
            case_id = "Output0"
            query_date_str = service.calculate_date_str(base_date_str, day_offset)
            
            # 直接查询 Output0 的数据
            balance_data = service.get_balance_data_by_case_id(
                db=db,
                case_id=case_id,
                date_str=query_date_str
            )
        else:
            # 自主申报：根据用户名生成 case_id（带降级处理）
            balance_data = service.get_balance_data_with_fallback(
                db=db,
                username=username,
                date_str=base_date_str,
                day_offset=day_offset
            )
        
        # 打印调试信息
        print(f"\n[能源平衡 API] 请求参数:")
        print(f"  day_index: {day_index}")
        print(f"  use_default_case: {use_default_case}")
        print(f"  username: {username}")
        print(f"  使用的 case_id: {balance_data.get('case_id')}")
        print(f"  查询的日期：{balance_data.get('date_str')}")
        print(f"  数据长度：thermal={len(balance_data['thermal'])}, wind={len(balance_data['wind'])}, "
              f"solar={len(balance_data['solar'])}, hydro={len(balance_data['hydro'])}, "
              f"load={len(balance_data['load'])}")
        
        return balance_data
    
    except Exception as e:
        print(f"[能源平衡 API] 获取数据失败：{e}")
        import traceback
        traceback.print_exc()
        # 返回空数据结构
        return {
            "thermal": [],
            "wind": [],
            "solar": [],
            "hydro": [],
            "load": [],
            "periods": 96,
            "date_str": "",
            "case_id": ""
        }


# ==================== 自主申报 - 机组中标结果 ====================

@router.get("/unit-bid-results")
def get_unit_bid_results(
    unit_id: str = Query(..., description="机组 ID，如 Thermal_1"),
    day_index: int = Query(1, description="第几天，从 1 开始（第一天=20260319）"),
    use_default_case: bool = Query(False, description="是否使用默认 case_id(Output0)，用于基线申报页面"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取机组中标结果数据（中标出力与均价）
    
    支持根据登录用户名和日期动态获取对应的机组中标数据
    - use_default_case=false: 根据用户名生成 case_id（如 G14->Output14）- 自主申报
    - use_default_case=true: 使用固定 Output0 - 基线申报
    - 查询指定机组的 sol_type 为'中标出力 (MW)'和'中标均价 (元/MWh)'的数据
    - 日期从 20260319 开始，第二天递增
    
    :param unit_id: 机组 ID
    :param day_index: 第几天，从 1 开始计数，第一天为 20260319
    :param use_default_case: 是否使用默认 case_id(Output0)
    :return: 包含 output_values（中标出力）, price_values（中标均价）, revenue_values（中标收益）的数据对象
    """
    try:
        # 基础日期
        base_date_str = "20260319"
        
        # 计算实际日期（day_index 从 1 开始，所以偏移量为 day_index - 1）
        day_offset = day_index - 1
        
        # 根据 use_default_case 参数决定 case_id
        if use_default_case:
            # 基线申报：使用固定的 Output0
            case_id = "Output0"
            username = "rational_declare"
        else:
            # 自主申报：根据用户名生成 case_id
            username = current_admin.username
            import re
            match = re.search(r'\d+', username)
            if match:
                num = match.group()
                case_id = f"Output{num}"
            else:
                # 如果用户名中没有数字，降级处理使用 Output0
                print(f"[机组中标结果 API] 警告：用户名 {username} 中没有数字，使用 Output0")
                case_id = "Output0"
        
        # 计算查询日期
        from datetime import timedelta
        base_date = datetime.strptime(base_date_str, "%Y%m%d")
        query_date = base_date + timedelta(days=day_offset)
        query_date_str = query_date.strftime("%Y%m%d")
        
        print(f"\n[机组中标结果 API] 请求参数:")
        print(f"  unit_id: {unit_id}")
        print(f"  day_index: {day_index}")
        print(f"  username: {username}")
        print(f"  生成的 case_id: {case_id}")
        print(f"  查询的日期：{query_date_str}")
        
        # 查询中标出力数据 - 使用 LIKE 模糊匹配以容忍空格等格式差异
        output_record = db.query(OutputUnitBidResults).filter(
            OutputUnitBidResults.unit_id == unit_id,
            OutputUnitBidResults.sol_type.like("%中标出力%"),
            OutputUnitBidResults.case_id == case_id,
            OutputUnitBidResults.date_str == query_date_str
        ).first()
        
        # 查询中标均价数据 - 使用 LIKE 模糊匹配以容忍空格等格式差异
        price_record = db.query(OutputUnitBidResults).filter(
            OutputUnitBidResults.unit_id == unit_id,
            OutputUnitBidResults.sol_type.like("%中标均价%"),
            OutputUnitBidResults.case_id == case_id,
            OutputUnitBidResults.date_str == query_date_str
        ).first()
        
        print(f"[机组中标结果 API] 初步查询结果:")
        print(f"  中标出力记录：{'✅ 找到' if output_record else '❌ 未找到'}")
        print(f"  中标均价记录：{'✅ 找到' if price_record else '❌ 未找到'}")
        
        # 如果没有找到数据，尝试使用 Output0
        if not output_record or not price_record:
            print(f"[机组中标结果 API] 警告：未找到 {case_id} 的数据，尝试使用 Output0")
            output_record = db.query(OutputUnitBidResults).filter(
                OutputUnitBidResults.unit_id == unit_id,
                OutputUnitBidResults.sol_type.like("%中标出力%"),
                OutputUnitBidResults.case_id == "Output0",
                OutputUnitBidResults.date_str == query_date_str
            ).first()
            
            price_record = db.query(OutputUnitBidResults).filter(
                OutputUnitBidResults.unit_id == unit_id,
                OutputUnitBidResults.sol_type.like("%中标均价%"),
                OutputUnitBidResults.case_id == "Output0",
                OutputUnitBidResults.date_str == query_date_str
            ).first()
            
            if output_record or price_record:
                print(f"[机组中标结果 API] 已从 Output0 获取数据")
        
        if not output_record and not price_record:
            # 诊断信息：数据库中实际存在的 case_id
            all_case_ids = db.query(OutputUnitBidResults.case_id).distinct().all()
            case_id_list = [c[0] for c in all_case_ids]
            
            # 诊断信息：数据库中实际存在的 sol_type
            all_sol_types = db.query(OutputUnitBidResults.sol_type).distinct().all()
            sol_type_list = [s[0] for s in all_sol_types]
            
            print(f"[机组中标结果 API] 错误：未找到机组 {unit_id} 在日期 {query_date_str} 的任何数据")
            print(f"[诊断信息]")
            print(f"  请求的 case_id: {case_id}")
            print(f"  数据库中存在的 case_id: {case_id_list}")
            print(f"  数据库中存在的 sol_type: {sol_type_list}")
            
            return {
                "output_values": [],
                "price_values": [],
                "revenue_values": [],
                "case_id": case_id,
                "date_str": query_date_str,
                "unit_id": unit_id
            }
        
        # 获取 t1-t96 的值
        output_values = output_record.period_values if output_record else [0.0] * 96
        price_values = price_record.period_values if price_record else [0.0] * 96
        
        # 计算中标收益：中标出力 × 中标均价 × 0.25
        revenue_values = []
        for i in range(96):
            output = output_values[i] if i < len(output_values) else 0.0
            price = price_values[i] if i < len(price_values) else 0.0
            revenue = output * price * 0.25
            revenue_values.append(revenue)
        
        print(f"[机组中标结果 API] 成功获取数据:")
        print(f"  中标出力有效数据点：{len([v for v in output_values if v > 0])}")
        print(f"  中标均价有效数据点：{len([v for v in price_values if v > 0])}")
        print(f"  中标收益有效数据点：{len([v for v in revenue_values if v > 0])}")
        
        return {
            "output_values": output_values,
            "price_values": price_values,
            "revenue_values": revenue_values,
            "case_id": case_id,
            "date_str": query_date_str,
            "unit_id": unit_id
        }
    
    except Exception as e:
        print(f"[机组中标结果 API] 获取数据失败：{e}")
        import traceback
        traceback.print_exc()
        return {
            "output_values": [],
            "price_values": [],
            "revenue_values": [],
            "case_id": "",
            "date_str": "",
            "unit_id": unit_id
        }


# === 策略报价分析接口 ===
from app.services.strategy_service import get_company_strategy_detail

@router.get("/strategy-detail/{plant_name}")
def get_strategy_detail(plant_name: str):
    detail = get_company_strategy_detail(plant_name)
    if not detail:
        return {"error": f"not found {plant_name}"}
    return detail


# === 策略生成与评价调用接口 ===
import subprocess, os

# 动态计算项目根目录
CURRENT_FILE = os.path.abspath(__file__)  # backend/app/api/routes/market.py
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE))))  # backend
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)  # project_package/code

# 策略脚本路径
STRATEGY_SCRIPT = os.path.join(PROJECT_ROOT, "market", "ROTS44_delivery", "code", "step2_bidding_strategy.py")
EVAL_SCRIPT = os.path.join(PROJECT_ROOT, "market", "ROTS44_delivery", "code", "step4_evaluation.py")
BASE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'market', 'Case', 'ROTS 44', 'Output0')

# 调试输出
print(f"[DEBUG] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[DEBUG] STRATEGY_SCRIPT: {STRATEGY_SCRIPT}")

@router.post("/run-strategy/{plant_name}")
def run_strategy_generation(plant_name: str):
    """调用 step2 为指定电厂生成竞价策略"""
    if not os.path.exists(STRATEGY_SCRIPT):
        return {"success": False, "error": f"step2 脚本不存在：{STRATEGY_SCRIPT}"}
    try:
        work_dir = os.path.dirname(STRATEGY_SCRIPT)
        config_file = os.path.join(os.path.dirname(STRATEGY_SCRIPT), "platform_config.ini")
        cmd = ["python", STRATEGY_SCRIPT, "--config", config_file, "--target", plant_name]
        print(f"[DEBUG] 执行命令：{' '.join(cmd)}")
        print(f"[DEBUG] 工作目录：{work_dir}")
        # 指定 encoding='utf-8' 避免 Windows 系统 GBK 编码问题
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, encoding='utf-8', timeout=300)
        print(f"[DEBUG] 返回码：{result.returncode}")
        print(f"[DEBUG] STDOUT: {result.stdout}")
        print(f"[DEBUG] STDERR: {result.stderr}")
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时 (300s)"}
    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}

@router.post("/run-evaluation/{plant_name}")
def run_strategy_evaluation(plant_name: str):
    """调用 step4 对指定电厂的策略进行出清后评价"""
    if not os.path.exists(EVAL_SCRIPT):
        return {"success": False, "error": f"step4 脚本不存在：{EVAL_SCRIPT}"}
    try:
        work_dir = os.path.dirname(EVAL_SCRIPT)
        cmd = ["python", EVAL_SCRIPT, "--target", plant_name, "--old", BASE_OUTPUT_DIR]
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时 (300s)"}
    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}

@router.post("/run-market-clearing")
def run_market_clearing():
    """执行市场出清批处理脚本 (execute.bat)"""
    batch_file = os.path.join(PROJECT_ROOT, "market", "execute.bat")
    if not os.path.exists(batch_file):
        return {"success": False, "error": f"批处理文件不存在：{batch_file}"}
    try:
        work_dir = os.path.dirname(batch_file)
        cmd = ["cmd", "/c", batch_file]
        print(f"[DEBUG] 执行市场出清命令：{' '.join(cmd)}")
        print(f"[DEBUG] 工作目录：{work_dir}")
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=600)
        print(f"[DEBUG] 返回码：{result.returncode}")
        print(f"[DEBUG] STDOUT: {result.stdout}")
        print(f"[DEBUG] STDERR: {result.stderr}")
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时 (600s)"}
    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}
