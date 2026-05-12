"""CSV文件解析服务"""
from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List

STANDARD_CSV_HEADERS = [
    "时间",
    "电价(元/kWh)",
    "负荷(kW)",
    "温度(℃)",
    "风速(m/s)",
    "云量(%)",
]

TIME_FORMATS = [
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
]


def _decode_csv_content(file_content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            return file_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法解析CSV文件编码，请使用UTF-8或GBK编码")


def _read_csv_rows(file_content: bytes) -> List[List[str]]:
    text_content = _decode_csv_content(file_content)
    reader = csv.reader(StringIO(text_content))
    return [[cell.strip() for cell in row] for row in reader]


def _parse_record_time(value: str, row_number: int) -> datetime:
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"第{row_number}行时间格式错误")


def _parse_float(value: str, column_name: str, row_number: int) -> float:
    if value == "":
        raise ValueError(f"第{row_number}行“{column_name}”不能为空")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"第{row_number}行“{column_name}”不是合法数字") from exc


def parse_csv_file(file_content: bytes) -> List[Dict[str, Any]]:
    """按任务一的严格模板解析CSV文件。"""
    rows = _read_csv_rows(file_content)
    if len(rows) < 2:
        raise ValueError("CSV文件至少需要包含表头和一行数据")

    headers = rows[0]
    if headers != STANDARD_CSV_HEADERS:
        raise ValueError(f"表头必须严格等于: {', '.join(STANDARD_CSV_HEADERS)}")

    records: List[Dict[str, Any]] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue
        if len(row) != len(STANDARD_CSV_HEADERS):
            raise ValueError(f"第{row_number}行列数不正确")

        record_time = _parse_record_time(row[0], row_number)
        price_kwh = _parse_float(row[1], STANDARD_CSV_HEADERS[1], row_number)
        load_kw = _parse_float(row[2], STANDARD_CSV_HEADERS[2], row_number)
        temperature = _parse_float(row[3], STANDARD_CSV_HEADERS[3], row_number)
        wind_speed = _parse_float(row[4], STANDARD_CSV_HEADERS[4], row_number)
        cloud_cover = _parse_float(row[5], STANDARD_CSV_HEADERS[5], row_number)

        if cloud_cover <= 30:
            weather_type = "晴"
        elif cloud_cover >= 70:
            weather_type = "阴"
        else:
            weather_type = "多云"

        records.append(
            {
                "record_time": record_time,
                "price_kwh": price_kwh,
                "generation_kwh": 0.0,
                "load_kw": load_kw,
                "temperature": temperature,
                "wind_speed": wind_speed,
                "cloud_cover": cloud_cover,
                "weather_type": weather_type,
                "is_holiday": False,
            }
        )

    if not records:
        raise ValueError("CSV文件至少需要包含一行有效数据")

    return records


def validate_csv_structure(file_content: bytes) -> tuple[bool, str]:
    """验证CSV文件是否符合任务一严格模板。"""
    try:
        parse_csv_file(file_content)
        return True, ""
    except ValueError as exc:
        return False, str(exc)
