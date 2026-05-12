"""电力电量平衡结果服务"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.output_power_balance import OutputPowerBalanceSheet


class PowerBalanceService:
    """电力电量平衡结果服务类"""
    
    # name 字段映射关系 - 前端英文键名 -> 数据库实际中文名称
    NAME_MAPPING = {
        "thermal": "火电功率",
        "wind": "风电消纳功率",      # 修改为数据库实际名称
        "solar": "光伏消纳功率",      # 修改为数据库实际名称
        "hydro": ["库容式水电功率", "径流式水电功率"],  # 支持多个水电类型，会合并
        "load": "总负荷功率"
    }
    
    @staticmethod
    def get_case_id_from_username(username: str) -> str:
        """根据用户名生成 case_id
        规则：G14 -> Output14, G13 -> Output13
        """
        import re
        match = re.search(r'\d+', username)
        if match:
            num = match.group()
            return f"Output{num}"
        return "Output0"
    
    @staticmethod
    def calculate_date_str(base_date_str: str, day_offset: int = 0) -> str:
        """计算日期字符串
        :param base_date_str: 基础日期，格式 YYYYMMDD
        :param day_offset: 偏移天数，0 表示第一天，1 表示第二天
        :return: 日期字符串，格式 YYYYMMDD
        """
        try:
            base_date = datetime.strptime(base_date_str, "%Y%m%d")
            target_date = base_date + timedelta(days=day_offset)
            return target_date.strftime("%Y%m%d")
        except Exception:
            # 如果解析失败，返回基础日期
            return base_date_str
    
    def get_balance_data(
        self,
        db: Session,
        username: str,
        date_str: str,
        day_offset: int = 0
    ) -> Dict[str, Any]:
        """获取电力电量平衡数据
        
        :param db: 数据库会话
        :param username: 当前登录用户名
        :param date_str: 基础日期字符串（如 20260319）
        :param day_offset: 日期偏移量（0 表示第一天，1 表示第二天）
        :return: 包含火电、风电、光伏、水电、总负荷数据的字典
        """
        # 计算实际查询的日期
        query_date_str = self.calculate_date_str(date_str, day_offset)
        
        # 根据用户名生成 case_id
        case_id = self.get_case_id_from_username(username)
        
        # 需要查询的 name 列表（处理列表类型的映射）
        target_names = []
        for name in self.NAME_MAPPING.values():
            if isinstance(name, list):
                target_names.extend(name)
            else:
                target_names.append(name)
        
        # 查询该日期和 case_id 的所有相关数据
        results = db.query(OutputPowerBalanceSheet).filter(
            OutputPowerBalanceSheet.date_str == query_date_str,
            OutputPowerBalanceSheet.case_id == case_id,
            OutputPowerBalanceSheet.name.in_(target_names)
        ).all()
        
        # 构建返回数据
        balance_data = {
            "thermal": [],
            "wind": [],
            "solar": [],
            "hydro": [],
            "load": [],
            "periods": 96,
            "date_str": query_date_str,
            "case_id": case_id
        }
        
        # 将查询结果填充到对应位置
        for row in results:
            if row.name == "火电功率":
                balance_data["thermal"] = row.period_values
            elif row.name == "风电消纳功率":
                balance_data["wind"] = row.period_values
            elif row.name == "光伏消纳功率":
                balance_data["solar"] = row.period_values
            elif row.name in ["库容式水电功率", "径流式水电功率"]:
                # 合并水电数据（如果有多个水电类型，累加）
                hydro_values = row.period_values
                if balance_data["hydro"]:
                    # 已存在水电数据，进行累加
                    existing = balance_data["hydro"]
                    balance_data["hydro"] = [
                        (existing[i] or 0) + (hydro_values[i] or 0) 
                        for i in range(96)
                    ]
                else:
                    balance_data["hydro"] = hydro_values
            elif row.name == "总负荷功率":
                balance_data["load"] = row.period_values
        
        return balance_data
    
    def get_balance_data_with_fallback(
        self,
        db: Session,
        username: str,
        date_str: str,
        day_offset: int = 0
    ) -> Dict[str, Any]:
        """获取电力电量平衡数据（带降级处理）
        
        如果个性化 case_id 没有数据，则尝试使用 Output0
        
        :param db: 数据库会话
        :param username: 当前登录用户名
        :param date_str: 基础日期字符串（如 20260319）
        :param day_offset: 日期偏移量（0 表示第一天，1 表示第二天）
        :return: 包含火电、风电、光伏、水电、总负荷数据的字典
        """
        result = self.get_balance_data(db, username, date_str, day_offset)
        
        # 检查是否有数据
        has_data = any([
            result["thermal"],
            result["wind"],
            result["solar"],
            result["hydro"],
            result["load"]
        ])
        
        # 如果没有数据，尝试使用 Output0
        if not has_data:
            case_id = "Output0"
            query_date_str = self.calculate_date_str(date_str, day_offset)
            
            # 需要查询的 name 列表（处理列表类型的映射）
            target_names = []
            for name in self.NAME_MAPPING.values():
                if isinstance(name, list):
                    target_names.extend(name)
                else:
                    target_names.append(name)
            
            results = db.query(OutputPowerBalanceSheet).filter(
                OutputPowerBalanceSheet.date_str == query_date_str,
                OutputPowerBalanceSheet.case_id == case_id,
                OutputPowerBalanceSheet.name.in_(target_names)
            ).all()
            
            result["case_id"] = case_id
            
            # 将查询结果填充到对应位置
            for row in results:
                if row.name == "火电功率":
                    result["thermal"] = row.period_values
                elif row.name == "风电消纳功率":
                    result["wind"] = row.period_values
                elif row.name == "光伏消纳功率":
                    result["solar"] = row.period_values
                elif row.name in ["库容式水电功率", "径流式水电功率"]:
                    hydro_values = row.period_values
                    if result["hydro"]:
                        existing = result["hydro"]
                        result["hydro"] = [
                            (existing[i] or 0) + (hydro_values[i] or 0) 
                            for i in range(96)
                        ]
                    else:
                        result["hydro"] = hydro_values
                elif row.name == "总负荷功率":
                    result["load"] = row.period_values
        
        return result
    
    def get_balance_data_by_case_id(
        self,
        db: Session,
        case_id: str,
        date_str: str
    ) -> Dict[str, Any]:
        """根据指定的 case_id 和日期获取电力电量平衡数据（用于基线申报）
        
        :param db: 数据库会话
        :param case_id: 指定的案例 ID（如 Output0）
        :param date_str: 日期字符串（如 20260319）
        :return: 包含 thermal, wind, solar, hydro, load 数组的数据字典
        """
        # 需要查询的 name 列表（处理列表类型的映射）
        target_names = []
        for name in self.NAME_MAPPING.values():
            if isinstance(name, list):
                target_names.extend(name)
            else:
                target_names.append(name)
        
        # 查询该日期和 case_id 的所有相关数据
        results = db.query(OutputPowerBalanceSheet).filter(
            OutputPowerBalanceSheet.date_str == date_str,
            OutputPowerBalanceSheet.case_id == case_id,
            OutputPowerBalanceSheet.name.in_(target_names)
        ).all()
        
        # 构建返回数据
        balance_data = {
            "thermal": [],
            "wind": [],
            "solar": [],
            "hydro": [],
            "load": [],
            "periods": 96,
            "date_str": date_str,
            "case_id": case_id
        }
        
        # 将查询结果填充到对应位置
        for row in results:
            if row.name == "火电功率":
                balance_data["thermal"] = row.period_values
            elif row.name == "风电消纳功率":
                balance_data["wind"] = row.period_values
            elif row.name == "光伏消纳功率":
                balance_data["solar"] = row.period_values
            elif row.name in ["库容式水电功率", "径流式水电功率"]:
                # 合并水电数据（如果有多个水电类型，累加）
                hydro_values = row.period_values
                if balance_data["hydro"]:
                    # 已存在水电数据，进行累加
                    existing = balance_data["hydro"]
                    balance_data["hydro"] = [
                        (existing[i] or 0) + (hydro_values[i] or 0) 
                        for i in range(96)
                    ]
                else:
                    balance_data["hydro"] = hydro_values
            elif row.name == "总负荷功率":
                balance_data["load"] = row.period_values
        
        return balance_data
