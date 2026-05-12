from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Float, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MarketThermalPlant(Base):
    """火电厂信息 (来源: ROTS 44_DM&ASInputData.xlsm / UnitThermalPlants)"""
    __tablename__ = "market_thermal_plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plant_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketThermalUnit(Base):
    """火电机组详细参数 (来源: ROTS 44_DM&ASInputData.xlsm / UnitThermalGenerators)"""
    __tablename__ = "market_thermal_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    unit_name: Mapped[str] = mapped_column(String(100))
    plant_id: Mapped[str] = mapped_column(String(50), index=True)
    bus_id: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[float] = mapped_column(Float)
    initial_state: Mapped[bool] = mapped_column(Boolean)
    initial_duration: Mapped[int] = mapped_column(Integer)
    min_output: Mapped[float] = mapped_column(Float)
    ramp_up: Mapped[float] = mapped_column(Float)
    ramp_down: Mapped[float] = mapped_column(Float)
    min_on_time: Mapped[int] = mapped_column(Integer)
    min_off_time: Mapped[int] = mapped_column(Integer)
    start_cost: Mapped[float] = mapped_column(Float)
    stop_cost: Mapped[float] = mapped_column(Float)
    fuel_id: Mapped[str] = mapped_column(String(50))
    cost_a: Mapped[float] = mapped_column(Float)
    cost_b: Mapped[float] = mapped_column(Float)
    cost_c: Mapped[float] = mapped_column(Float)
    freq_response: Mapped[float] = mapped_column(Float)
    freq_error: Mapped[float] = mapped_column(Float)
    reg_speed: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketWindUnit(Base):
    """风电机组信息 (来源: ROTS 44_DM&ASInputData.xlsm / UnitWindGenerators)"""
    __tablename__ = "market_wind_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    unit_name: Mapped[str] = mapped_column(String(100))
    bus_id: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[float] = mapped_column(Float)
    curve_name: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketSolarUnit(Base):
    """光伏机组信息 (来源: ROTS 44_DM&ASInputData.xlsm / UnitSolarGenerators)"""
    __tablename__ = "market_solar_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    unit_name: Mapped[str] = mapped_column(String(100))
    bus_id: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[float] = mapped_column(Float)
    curve_name: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketClearingHistory(Base):
    """成交历史数据 (来源: ROTS_合并数据_按顺序.xlsx)
    每行存一个指标的所有时段数据(JSON数组)
    """
    __tablename__ = "market_clearing_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    period_values: Mapped[dict] = mapped_column(JSON)
    total_periods: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketOutResult(Base):
    """市场出清结果时序数据 (来源: out.xlsx)
    每行存一个sheet中一个单元(机组/节点)的96个时段数据
    """
    __tablename__ = "market_out_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sheet_name: Mapped[str] = mapped_column(String(100), index=True)
    row_index: Mapped[int] = mapped_column(Integer)
    period_values: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketDayAheadQuote(Base):
    """日前市场机组报价 (来源: ROTS 44_DM&ASInputData.xlsm / MarDayAheadUnitQuotes)"""
    __tablename__ = "market_day_ahead_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(Integer)
    unit_id: Mapped[str] = mapped_column(String(50), index=True)
    market_name: Mapped[str] = mapped_column(String(50))
    quote_time: Mapped[int] = mapped_column(Integer)
    quote_section: Mapped[str] = mapped_column(String(50))
    quote_price: Mapped[float] = mapped_column(Float)
    quote_quantity: Mapped[float] = mapped_column(Float)
    is_used: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InputDayAheadUnitQuote(Base):
    """输入日前市场机组报价 (来源：input_dayahead_unit_quotes)"""
    __tablename__ = "input_dayahead_unit_quotes"

    # 该表没有 id 自增列，使用 QuoteId 作为主键
    QuoteId: Mapped[int] = mapped_column(Integer, primary_key=True)
    UnitId: Mapped[str] = mapped_column(String(50), index=True)
    MarketName: Mapped[str] = mapped_column(String(50))
    QuoteTime: Mapped[int] = mapped_column(Integer)
    QuoteSection: Mapped[str] = mapped_column(String(50))
    QuotePrice: Mapped[float] = mapped_column(Float)
    QuoteCapacity: Mapped[float] = mapped_column(Float)
    IsUsed: Mapped[bool] = mapped_column(Boolean)
    case_id: Mapped[str] = mapped_column(String(50), index=True)
    data_date: Mapped[str] = mapped_column(String(50), index=True)




class MarketLoad(Base):
    """负荷数据 (来源: ROTS 44_DM&ASInputData.xlsm / Loads)"""
    __tablename__ = "market_loads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    load_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    load_name: Mapped[str] = mapped_column(String(100))
    bus_id: Mapped[str] = mapped_column(String(50))
    load_curve_name: Mapped[str] = mapped_column(String(100))
    capacity_ratio: Mapped[float] = mapped_column(Float)
    responsiveness: Mapped[float] = mapped_column(Float)
    is_interrupt: Mapped[bool] = mapped_column(Boolean)
    is_transfer: Mapped[bool] = mapped_column(Boolean)
    interrupt_cost: Mapped[float] = mapped_column(Float)
    transfer_cost: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OutputEnergyMarketOverview(Base):
    """电能量市场概览数据 (来源：output_energy_market_overview)"""
    __tablename__ = "output_energy_market_overview"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_name: Mapped[str] = mapped_column('市场名称', Text, nullable=True)
    spot_market: Mapped[float] = mapped_column('现货市场', Float, nullable=True)
    case_id: Mapped[str] = mapped_column(Text, nullable=True)
    date_str: Mapped[str] = mapped_column(Text, nullable=True)


class OutputThermalPlantRevenue(Base):
    """火电厂收益数据 (来源：output_thermal_plant_revenue)"""
    __tablename__ = "output_thermal_plant_revenue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    operation_cost: Mapped[str] = mapped_column(Text, nullable=True)
    open_cost: Mapped[str] = mapped_column(Text, nullable=True)
    close_cost: Mapped[int] = mapped_column(Integer, nullable=True)
    bid_quantity: Mapped[str] = mapped_column(Text, nullable=True)
    bid_average_price: Mapped[str] = mapped_column(Text, nullable=True)
    bid_revenue: Mapped[str] = mapped_column(Text, nullable=True)
    net_revenue: Mapped[str] = mapped_column(Text, nullable=True)
    case_id: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    date_str: Mapped[str] = mapped_column(String(50), index=True, nullable=True)


class OutputClearingPrice(Base):
    """电能量市场出清价格数据 (来源：output_clearing_price)
    存储每个母线在不同价格类型下的 96 个时段出清电价
    """
    __tablename__ = "output_clearing_price"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bus_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    price_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    t1: Mapped[str] = mapped_column(Text, nullable=True)
    t2: Mapped[str] = mapped_column(Text, nullable=True)
    t3: Mapped[str] = mapped_column(Text, nullable=True)
    t4: Mapped[str] = mapped_column(Text, nullable=True)
    t5: Mapped[str] = mapped_column(Text, nullable=True)
    t6: Mapped[str] = mapped_column(Text, nullable=True)
    t7: Mapped[str] = mapped_column(Text, nullable=True)
    t8: Mapped[str] = mapped_column(Text, nullable=True)
    t9: Mapped[str] = mapped_column(Text, nullable=True)
    t10: Mapped[str] = mapped_column(Text, nullable=True)
    t11: Mapped[str] = mapped_column(Text, nullable=True)
    t12: Mapped[str] = mapped_column(Text, nullable=True)
    t13: Mapped[str] = mapped_column(Text, nullable=True)
    t14: Mapped[str] = mapped_column(Text, nullable=True)
    t15: Mapped[str] = mapped_column(Text, nullable=True)
    t16: Mapped[str] = mapped_column(Text, nullable=True)
    t17: Mapped[str] = mapped_column(Text, nullable=True)
    t18: Mapped[str] = mapped_column(Text, nullable=True)
    t19: Mapped[str] = mapped_column(Text, nullable=True)
    t20: Mapped[str] = mapped_column(Text, nullable=True)
    t21: Mapped[str] = mapped_column(Text, nullable=True)
    t22: Mapped[str] = mapped_column(Text, nullable=True)
    t23: Mapped[str] = mapped_column(Text, nullable=True)
    t24: Mapped[str] = mapped_column(Text, nullable=True)
    t25: Mapped[str] = mapped_column(Text, nullable=True)
    t26: Mapped[str] = mapped_column(Text, nullable=True)
    t27: Mapped[str] = mapped_column(Text, nullable=True)
    t28: Mapped[str] = mapped_column(Text, nullable=True)
    t29: Mapped[str] = mapped_column(Text, nullable=True)
    t30: Mapped[str] = mapped_column(Text, nullable=True)
    t31: Mapped[str] = mapped_column(Text, nullable=True)
    t32: Mapped[str] = mapped_column(Text, nullable=True)
    t33: Mapped[str] = mapped_column(Text, nullable=True)
    t34: Mapped[str] = mapped_column(Text, nullable=True)
    t35: Mapped[str] = mapped_column(Text, nullable=True)
    t36: Mapped[str] = mapped_column(Text, nullable=True)
    t37: Mapped[str] = mapped_column(Text, nullable=True)
    t38: Mapped[str] = mapped_column(Text, nullable=True)
    t39: Mapped[str] = mapped_column(Text, nullable=True)
    t40: Mapped[str] = mapped_column(Text, nullable=True)
    t41: Mapped[str] = mapped_column(Text, nullable=True)
    t42: Mapped[str] = mapped_column(Text, nullable=True)
    t43: Mapped[str] = mapped_column(Text, nullable=True)
    t44: Mapped[str] = mapped_column(Text, nullable=True)
    t45: Mapped[str] = mapped_column(Text, nullable=True)
    t46: Mapped[str] = mapped_column(Text, nullable=True)
    t47: Mapped[str] = mapped_column(Text, nullable=True)
    t48: Mapped[str] = mapped_column(Text, nullable=True)
    t49: Mapped[str] = mapped_column(Text, nullable=True)
    t50: Mapped[str] = mapped_column(Text, nullable=True)
    t51: Mapped[str] = mapped_column(Text, nullable=True)
    t52: Mapped[str] = mapped_column(Text, nullable=True)
    t53: Mapped[str] = mapped_column(Text, nullable=True)
    t54: Mapped[str] = mapped_column(Text, nullable=True)
    t55: Mapped[str] = mapped_column(Text, nullable=True)
    t56: Mapped[str] = mapped_column(Text, nullable=True)
    t57: Mapped[str] = mapped_column(Text, nullable=True)
    t58: Mapped[str] = mapped_column(Text, nullable=True)
    t59: Mapped[str] = mapped_column(Text, nullable=True)
    t60: Mapped[str] = mapped_column(Text, nullable=True)
    t61: Mapped[str] = mapped_column(Text, nullable=True)
    t62: Mapped[str] = mapped_column(Text, nullable=True)
    t63: Mapped[str] = mapped_column(Text, nullable=True)
    t64: Mapped[str] = mapped_column(Text, nullable=True)
    t65: Mapped[str] = mapped_column(Text, nullable=True)
    t66: Mapped[str] = mapped_column(Text, nullable=True)
    t67: Mapped[str] = mapped_column(Text, nullable=True)
    t68: Mapped[str] = mapped_column(Text, nullable=True)
    t69: Mapped[str] = mapped_column(Text, nullable=True)
    t70: Mapped[str] = mapped_column(Text, nullable=True)
    t71: Mapped[str] = mapped_column(Text, nullable=True)
    t72: Mapped[str] = mapped_column(Text, nullable=True)
    t73: Mapped[str] = mapped_column(Text, nullable=True)
    t74: Mapped[str] = mapped_column(Text, nullable=True)
    t75: Mapped[str] = mapped_column(Text, nullable=True)
    t76: Mapped[str] = mapped_column(Text, nullable=True)
    t77: Mapped[str] = mapped_column(Text, nullable=True)
    t78: Mapped[str] = mapped_column(Text, nullable=True)
    t79: Mapped[str] = mapped_column(Text, nullable=True)
    t80: Mapped[str] = mapped_column(Text, nullable=True)
    t81: Mapped[str] = mapped_column(Text, nullable=True)
    t82: Mapped[str] = mapped_column(Text, nullable=True)
    t83: Mapped[str] = mapped_column(Text, nullable=True)
    t84: Mapped[str] = mapped_column(Text, nullable=True)
    t85: Mapped[str] = mapped_column(Text, nullable=True)
    t86: Mapped[str] = mapped_column(Text, nullable=True)
    t87: Mapped[str] = mapped_column(Text, nullable=True)
    t88: Mapped[str] = mapped_column(Text, nullable=True)
    t89: Mapped[str] = mapped_column(Text, nullable=True)
    t90: Mapped[str] = mapped_column(Text, nullable=True)
    t91: Mapped[str] = mapped_column(Text, nullable=True)
    t92: Mapped[str] = mapped_column(Text, nullable=True)
    t93: Mapped[str] = mapped_column(Text, nullable=True)
    t94: Mapped[str] = mapped_column(Text, nullable=True)
    t95: Mapped[str] = mapped_column(Text, nullable=True)
    t96: Mapped[str] = mapped_column(Text, nullable=True)
    case_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    date_str: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
