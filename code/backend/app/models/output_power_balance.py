from __future__ import annotations

from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OutputPowerBalanceSheet(Base):
    """输出功率平衡表 (自主申报页面用)
    存储火电、风电、光伏、水电、总负荷的功率数据
    来源：output_power_balance_sheet 表
    
    用户名与 case_id 对应关系：用户名 G14 -> case_id Output14
    起始日期：20260319
    
    注意：该表有 id 自增列作为主键
    """
    __tablename__ = "output_power_balance_sheet"

    # id 自增列作为主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    
    # 数据字段
    name: Mapped[str] = mapped_column(String(100), index=True, comment="名称（火电功率/风电功率/光伏功率/水电功率/总负荷功率）")
    case_id: Mapped[str] = mapped_column(String(50), index=True, comment="案例 ID（Output0, Output14, ...）")
    date_str: Mapped[str] = mapped_column(String(20), index=True, comment="日期字符串（如 20260319）")
    
    # t1-t96 时段数据 - 使用 Column 显式映射每个字段
    t1: Mapped[float] = mapped_column('t1', Float, nullable=True)
    t2: Mapped[float] = mapped_column('t2', Float, nullable=True)
    t3: Mapped[float] = mapped_column('t3', Float, nullable=True)
    t4: Mapped[float] = mapped_column('t4', Float, nullable=True)
    t5: Mapped[float] = mapped_column('t5', Float, nullable=True)
    t6: Mapped[float] = mapped_column('t6', Float, nullable=True)
    t7: Mapped[float] = mapped_column('t7', Float, nullable=True)
    t8: Mapped[float] = mapped_column('t8', Float, nullable=True)
    t9: Mapped[float] = mapped_column('t9', Float, nullable=True)
    t10: Mapped[float] = mapped_column('t10', Float, nullable=True)
    t11: Mapped[float] = mapped_column('t11', Float, nullable=True)
    t12: Mapped[float] = mapped_column('t12', Float, nullable=True)
    t13: Mapped[float] = mapped_column('t13', Float, nullable=True)
    t14: Mapped[float] = mapped_column('t14', Float, nullable=True)
    t15: Mapped[float] = mapped_column('t15', Float, nullable=True)
    t16: Mapped[float] = mapped_column('t16', Float, nullable=True)
    t17: Mapped[float] = mapped_column('t17', Float, nullable=True)
    t18: Mapped[float] = mapped_column('t18', Float, nullable=True)
    t19: Mapped[float] = mapped_column('t19', Float, nullable=True)
    t20: Mapped[float] = mapped_column('t20', Float, nullable=True)
    t21: Mapped[float] = mapped_column('t21', Float, nullable=True)
    t22: Mapped[float] = mapped_column('t22', Float, nullable=True)
    t23: Mapped[float] = mapped_column('t23', Float, nullable=True)
    t24: Mapped[float] = mapped_column('t24', Float, nullable=True)
    t25: Mapped[float] = mapped_column('t25', Float, nullable=True)
    t26: Mapped[float] = mapped_column('t26', Float, nullable=True)
    t27: Mapped[float] = mapped_column('t27', Float, nullable=True)
    t28: Mapped[float] = mapped_column('t28', Float, nullable=True)
    t29: Mapped[float] = mapped_column('t29', Float, nullable=True)
    t30: Mapped[float] = mapped_column('t30', Float, nullable=True)
    t31: Mapped[float] = mapped_column('t31', Float, nullable=True)
    t32: Mapped[float] = mapped_column('t32', Float, nullable=True)
    t33: Mapped[float] = mapped_column('t33', Float, nullable=True)
    t34: Mapped[float] = mapped_column('t34', Float, nullable=True)
    t35: Mapped[float] = mapped_column('t35', Float, nullable=True)
    t36: Mapped[float] = mapped_column('t36', Float, nullable=True)
    t37: Mapped[float] = mapped_column('t37', Float, nullable=True)
    t38: Mapped[float] = mapped_column('t38', Float, nullable=True)
    t39: Mapped[float] = mapped_column('t39', Float, nullable=True)
    t40: Mapped[float] = mapped_column('t40', Float, nullable=True)
    t41: Mapped[float] = mapped_column('t41', Float, nullable=True)
    t42: Mapped[float] = mapped_column('t42', Float, nullable=True)
    t43: Mapped[float] = mapped_column('t43', Float, nullable=True)
    t44: Mapped[float] = mapped_column('t44', Float, nullable=True)
    t45: Mapped[float] = mapped_column('t45', Float, nullable=True)
    t46: Mapped[float] = mapped_column('t46', Float, nullable=True)
    t47: Mapped[float] = mapped_column('t47', Float, nullable=True)
    t48: Mapped[float] = mapped_column('t48', Float, nullable=True)
    t49: Mapped[float] = mapped_column('t49', Float, nullable=True)
    t50: Mapped[float] = mapped_column('t50', Float, nullable=True)
    t51: Mapped[float] = mapped_column('t51', Float, nullable=True)
    t52: Mapped[float] = mapped_column('t52', Float, nullable=True)
    t53: Mapped[float] = mapped_column('t53', Float, nullable=True)
    t54: Mapped[float] = mapped_column('t54', Float, nullable=True)
    t55: Mapped[float] = mapped_column('t55', Float, nullable=True)
    t56: Mapped[float] = mapped_column('t56', Float, nullable=True)
    t57: Mapped[float] = mapped_column('t57', Float, nullable=True)
    t58: Mapped[float] = mapped_column('t58', Float, nullable=True)
    t59: Mapped[float] = mapped_column('t59', Float, nullable=True)
    t60: Mapped[float] = mapped_column('t60', Float, nullable=True)
    t61: Mapped[float] = mapped_column('t61', Float, nullable=True)
    t62: Mapped[float] = mapped_column('t62', Float, nullable=True)
    t63: Mapped[float] = mapped_column('t63', Float, nullable=True)
    t64: Mapped[float] = mapped_column('t64', Float, nullable=True)
    t65: Mapped[float] = mapped_column('t65', Float, nullable=True)
    t66: Mapped[float] = mapped_column('t66', Float, nullable=True)
    t67: Mapped[float] = mapped_column('t67', Float, nullable=True)
    t68: Mapped[float] = mapped_column('t68', Float, nullable=True)
    t69: Mapped[float] = mapped_column('t69', Float, nullable=True)
    t70: Mapped[float] = mapped_column('t70', Float, nullable=True)
    t71: Mapped[float] = mapped_column('t71', Float, nullable=True)
    t72: Mapped[float] = mapped_column('t72', Float, nullable=True)
    t73: Mapped[float] = mapped_column('t73', Float, nullable=True)
    t74: Mapped[float] = mapped_column('t74', Float, nullable=True)
    t75: Mapped[float] = mapped_column('t75', Float, nullable=True)
    t76: Mapped[float] = mapped_column('t76', Float, nullable=True)
    t77: Mapped[float] = mapped_column('t77', Float, nullable=True)
    t78: Mapped[float] = mapped_column('t78', Float, nullable=True)
    t79: Mapped[float] = mapped_column('t79', Float, nullable=True)
    t80: Mapped[float] = mapped_column('t80', Float, nullable=True)
    t81: Mapped[float] = mapped_column('t81', Float, nullable=True)
    t82: Mapped[float] = mapped_column('t82', Float, nullable=True)
    t83: Mapped[float] = mapped_column('t83', Float, nullable=True)
    t84: Mapped[float] = mapped_column('t84', Float, nullable=True)
    t85: Mapped[float] = mapped_column('t85', Float, nullable=True)
    t86: Mapped[float] = mapped_column('t86', Float, nullable=True)
    t87: Mapped[float] = mapped_column('t87', Float, nullable=True)
    t88: Mapped[float] = mapped_column('t88', Float, nullable=True)
    t89: Mapped[float] = mapped_column('t89', Float, nullable=True)
    t90: Mapped[float] = mapped_column('t90', Float, nullable=True)
    t91: Mapped[float] = mapped_column('t91', Float, nullable=True)
    t92: Mapped[float] = mapped_column('t92', Float, nullable=True)
    t93: Mapped[float] = mapped_column('t93', Float, nullable=True)
    t94: Mapped[float] = mapped_column('t94', Float, nullable=True)
    t95: Mapped[float] = mapped_column('t95', Float, nullable=True)
    t96: Mapped[float] = mapped_column('t96', Float, nullable=True)
    
    
    @property
    def period_values(self) -> list:
        """将 t1-t96 转换为列表格式返回"""
        return [
            getattr(self, f't{i}', None) 
            for i in range(1, 97)
        ]


class OutputUnitBidResults(Base):
    """机组中标结果表 (自主申报页面详情分析用)
    存储各机组的中标出力和中标均价数据
    来源：output_unit_bid_results 表
    
    用户名与 case_id 对应关系：用户名 G14 -> case_id Output14
    起始日期：20260319
    sol_type: '中标出力 (MW)' 或 '中标均价 (元/MWh)'
    
    注意：该表有 id 自增列作为主键
    """
    __tablename__ = "output_unit_bid_results"

    # id 自增列作为主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    
    # 数据字段
    unit_id: Mapped[str] = mapped_column(String(100), index=True, comment="机组 ID")
    sol_type: Mapped[str] = mapped_column(String(100), index=True, comment="结果类型（中标出力 (MW)/中标均价 (元/MWh)）")
    case_id: Mapped[str] = mapped_column(String(50), index=True, comment="案例 ID（Output0, Output14, ...）")
    date_str: Mapped[str] = mapped_column(String(20), index=True, comment="日期字符串（如 20260319）")
    
    # t1-t96 时段数据 - 使用 Column 显式映射每个字段（TEXT 类型，需要转换为 float）
    t1: Mapped[float] = mapped_column('t1', Float, nullable=True)
    t2: Mapped[float] = mapped_column('t2', Float, nullable=True)
    t3: Mapped[float] = mapped_column('t3', Float, nullable=True)
    t4: Mapped[float] = mapped_column('t4', Float, nullable=True)
    t5: Mapped[float] = mapped_column('t5', Float, nullable=True)
    t6: Mapped[float] = mapped_column('t6', Float, nullable=True)
    t7: Mapped[float] = mapped_column('t7', Float, nullable=True)
    t8: Mapped[float] = mapped_column('t8', Float, nullable=True)
    t9: Mapped[float] = mapped_column('t9', Float, nullable=True)
    t10: Mapped[float] = mapped_column('t10', Float, nullable=True)
    t11: Mapped[float] = mapped_column('t11', Float, nullable=True)
    t12: Mapped[float] = mapped_column('t12', Float, nullable=True)
    t13: Mapped[float] = mapped_column('t13', Float, nullable=True)
    t14: Mapped[float] = mapped_column('t14', Float, nullable=True)
    t15: Mapped[float] = mapped_column('t15', Float, nullable=True)
    t16: Mapped[float] = mapped_column('t16', Float, nullable=True)
    t17: Mapped[float] = mapped_column('t17', Float, nullable=True)
    t18: Mapped[float] = mapped_column('t18', Float, nullable=True)
    t19: Mapped[float] = mapped_column('t19', Float, nullable=True)
    t20: Mapped[float] = mapped_column('t20', Float, nullable=True)
    t21: Mapped[float] = mapped_column('t21', Float, nullable=True)
    t22: Mapped[float] = mapped_column('t22', Float, nullable=True)
    t23: Mapped[float] = mapped_column('t23', Float, nullable=True)
    t24: Mapped[float] = mapped_column('t24', Float, nullable=True)
    t25: Mapped[float] = mapped_column('t25', Float, nullable=True)
    t26: Mapped[float] = mapped_column('t26', Float, nullable=True)
    t27: Mapped[float] = mapped_column('t27', Float, nullable=True)
    t28: Mapped[float] = mapped_column('t28', Float, nullable=True)
    t29: Mapped[float] = mapped_column('t29', Float, nullable=True)
    t30: Mapped[float] = mapped_column('t30', Float, nullable=True)
    t31: Mapped[float] = mapped_column('t31', Float, nullable=True)
    t32: Mapped[float] = mapped_column('t32', Float, nullable=True)
    t33: Mapped[float] = mapped_column('t33', Float, nullable=True)
    t34: Mapped[float] = mapped_column('t34', Float, nullable=True)
    t35: Mapped[float] = mapped_column('t35', Float, nullable=True)
    t36: Mapped[float] = mapped_column('t36', Float, nullable=True)
    t37: Mapped[float] = mapped_column('t37', Float, nullable=True)
    t38: Mapped[float] = mapped_column('t38', Float, nullable=True)
    t39: Mapped[float] = mapped_column('t39', Float, nullable=True)
    t40: Mapped[float] = mapped_column('t40', Float, nullable=True)
    t41: Mapped[float] = mapped_column('t41', Float, nullable=True)
    t42: Mapped[float] = mapped_column('t42', Float, nullable=True)
    t43: Mapped[float] = mapped_column('t43', Float, nullable=True)
    t44: Mapped[float] = mapped_column('t44', Float, nullable=True)
    t45: Mapped[float] = mapped_column('t45', Float, nullable=True)
    t46: Mapped[float] = mapped_column('t46', Float, nullable=True)
    t47: Mapped[float] = mapped_column('t47', Float, nullable=True)
    t48: Mapped[float] = mapped_column('t48', Float, nullable=True)
    t49: Mapped[float] = mapped_column('t49', Float, nullable=True)
    t50: Mapped[float] = mapped_column('t50', Float, nullable=True)
    t51: Mapped[float] = mapped_column('t51', Float, nullable=True)
    t52: Mapped[float] = mapped_column('t52', Float, nullable=True)
    t53: Mapped[float] = mapped_column('t53', Float, nullable=True)
    t54: Mapped[float] = mapped_column('t54', Float, nullable=True)
    t55: Mapped[float] = mapped_column('t55', Float, nullable=True)
    t56: Mapped[float] = mapped_column('t56', Float, nullable=True)
    t57: Mapped[float] = mapped_column('t57', Float, nullable=True)
    t58: Mapped[float] = mapped_column('t58', Float, nullable=True)
    t59: Mapped[float] = mapped_column('t59', Float, nullable=True)
    t60: Mapped[float] = mapped_column('t60', Float, nullable=True)
    t61: Mapped[float] = mapped_column('t61', Float, nullable=True)
    t62: Mapped[float] = mapped_column('t62', Float, nullable=True)
    t63: Mapped[float] = mapped_column('t63', Float, nullable=True)
    t64: Mapped[float] = mapped_column('t64', Float, nullable=True)
    t65: Mapped[float] = mapped_column('t65', Float, nullable=True)
    t66: Mapped[float] = mapped_column('t66', Float, nullable=True)
    t67: Mapped[float] = mapped_column('t67', Float, nullable=True)
    t68: Mapped[float] = mapped_column('t68', Float, nullable=True)
    t69: Mapped[float] = mapped_column('t69', Float, nullable=True)
    t70: Mapped[float] = mapped_column('t70', Float, nullable=True)
    t71: Mapped[float] = mapped_column('t71', Float, nullable=True)
    t72: Mapped[float] = mapped_column('t72', Float, nullable=True)
    t73: Mapped[float] = mapped_column('t73', Float, nullable=True)
    t74: Mapped[float] = mapped_column('t74', Float, nullable=True)
    t75: Mapped[float] = mapped_column('t75', Float, nullable=True)
    t76: Mapped[float] = mapped_column('t76', Float, nullable=True)
    t77: Mapped[float] = mapped_column('t77', Float, nullable=True)
    t78: Mapped[float] = mapped_column('t78', Float, nullable=True)
    t79: Mapped[float] = mapped_column('t79', Float, nullable=True)
    t80: Mapped[float] = mapped_column('t80', Float, nullable=True)
    t81: Mapped[float] = mapped_column('t81', Float, nullable=True)
    t82: Mapped[float] = mapped_column('t82', Float, nullable=True)
    t83: Mapped[float] = mapped_column('t83', Float, nullable=True)
    t84: Mapped[float] = mapped_column('t84', Float, nullable=True)
    t85: Mapped[float] = mapped_column('t85', Float, nullable=True)
    t86: Mapped[float] = mapped_column('t86', Float, nullable=True)
    t87: Mapped[float] = mapped_column('t87', Float, nullable=True)
    t88: Mapped[float] = mapped_column('t88', Float, nullable=True)
    t89: Mapped[float] = mapped_column('t89', Float, nullable=True)
    t90: Mapped[float] = mapped_column('t90', Float, nullable=True)
    t91: Mapped[float] = mapped_column('t91', Float, nullable=True)
    t92: Mapped[float] = mapped_column('t92', Float, nullable=True)
    t93: Mapped[float] = mapped_column('t93', Float, nullable=True)
    t94: Mapped[float] = mapped_column('t94', Float, nullable=True)
    t95: Mapped[float] = mapped_column('t95', Float, nullable=True)
    t96: Mapped[float] = mapped_column('t96', Float, nullable=True)
    
    
    @property
    def period_values(self) -> list:
        """将 t1-t96 转换为列表格式返回"""
        return [
            getattr(self, f't{i}', None) 
            for i in range(1, 97)
        ]
