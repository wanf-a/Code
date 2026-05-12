from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List

import openpyxl


STANDARD_XLSX_HEADERS = [
    "时间",
    "电价(元/kWh)",
    "负荷(kW)",
    "温度(℃)",
    "风速(m/s)",
    "云量(%)",
]

STANDARD_XLSX_FIELD_NAMES = [
    "Time",
    "Price",
    "Load",
    "Temperature",
    "WindSpeed",
    "CloudCover",
]

STANDARD_XLSX_TYPE_NAMES = [
    "datetime",
    "Double",
    "Double",
    "Double",
    "Double",
    "Double",
]

TIME_FORMATS = [
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
]


def _is_empty_cell(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _is_empty_row(values: List[object]) -> bool:
    return all(_is_empty_cell(value) for value in values)


def _parse_excel_record_time(value: object, row_number: int) -> datetime:
    if _is_empty_cell(value):
        raise ValueError(f"第{row_number}行时间不能为空")

    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(f"第{row_number}行时间格式错误")


def _parse_excel_float(value: object, column_name: str, row_number: int) -> float:
    if _is_empty_cell(value):
        raise ValueError(f"第{row_number}行{column_name}不能为空")

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"第{row_number}行{column_name}不是合法数字") from exc


def _validate_excel_value_range(value: float, column_name: str, row_number: int) -> float:
    if column_name == STANDARD_XLSX_HEADERS[1] and value < 0:
        raise ValueError(f"第{row_number}行{column_name}不能小于0")
    if column_name == STANDARD_XLSX_HEADERS[2] and value < 0:
        raise ValueError(f"第{row_number}行{column_name}不能小于0")
    if column_name == STANDARD_XLSX_HEADERS[4] and value < 0:
        raise ValueError(f"第{row_number}行{column_name}不能小于0")
    if column_name == STANDARD_XLSX_HEADERS[5] and not 0 <= value <= 100:
        raise ValueError(f"第{row_number}行{column_name}必须在0到100之间")
    return value


def _parse_excel_schema_row(row_values: List[object], row_number: int) -> List[object]:
    schema_column_count = len(STANDARD_XLSX_HEADERS)
    schema_values = row_values[:schema_column_count]
    extra_values = row_values[schema_column_count:]

    if any(not _is_empty_cell(value) for value in extra_values):
        raise ValueError(f"第{row_number}行存在超出模板的额外列数据")

    if len(schema_values) < schema_column_count:
        schema_values.extend([None] * (schema_column_count - len(schema_values)))

    return schema_values


def _derive_weather_type(cloud_cover: float) -> str:
    if cloud_cover <= 30:
        return "晴"
    if cloud_cover >= 70:
        return "阴"
    return "多云"


def parse_excel_file(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse the first worksheet in read-only mode for large uploads."""
    workbook = openpyxl.load_workbook(BytesIO(file_content), read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows)
            field_name_row = next(rows)
            type_name_row = next(rows)
        except StopIteration as exc:
            raise ValueError("Excel文件至少需要包含三行模板说明和一行数据") from exc

        headers = [str(cell).strip() if cell is not None else "" for cell in header_row[: len(STANDARD_XLSX_HEADERS)]]
        if headers != STANDARD_XLSX_HEADERS:
            raise ValueError(f"表头必须严格等于: {', '.join(STANDARD_XLSX_HEADERS)}")
        if any(not _is_empty_cell(value) for value in header_row[len(STANDARD_XLSX_HEADERS):]):
            raise ValueError(f"表头必须严格等于: {', '.join(STANDARD_XLSX_HEADERS)}")

        field_names = [str(cell).strip() if cell is not None else "" for cell in field_name_row[: len(STANDARD_XLSX_FIELD_NAMES)]]
        if field_names != STANDARD_XLSX_FIELD_NAMES:
            raise ValueError(f"第2行必须严格等于: {', '.join(STANDARD_XLSX_FIELD_NAMES)}")
        if any(not _is_empty_cell(value) for value in field_name_row[len(STANDARD_XLSX_FIELD_NAMES):]):
            raise ValueError(f"第2行必须严格等于: {', '.join(STANDARD_XLSX_FIELD_NAMES)}")

        type_names = [str(cell).strip() if cell is not None else "" for cell in type_name_row[: len(STANDARD_XLSX_TYPE_NAMES)]]
        if type_names != STANDARD_XLSX_TYPE_NAMES:
            raise ValueError(f"第3行必须严格等于: {', '.join(STANDARD_XLSX_TYPE_NAMES)}")
        if any(not _is_empty_cell(value) for value in type_name_row[len(STANDARD_XLSX_TYPE_NAMES):]):
            raise ValueError(f"第3行必须严格等于: {', '.join(STANDARD_XLSX_TYPE_NAMES)}")

        records: List[Dict[str, Any]] = []
        for row_number, row_values_tuple in enumerate(rows, start=4):
            row_values = list(row_values_tuple)
            if _is_empty_row(row_values):
                continue

            schema_values = _parse_excel_schema_row(row_values, row_number)
            record_time = _parse_excel_record_time(schema_values[0], row_number)
            price_kwh = _validate_excel_value_range(
                _parse_excel_float(schema_values[1], STANDARD_XLSX_HEADERS[1], row_number),
                STANDARD_XLSX_HEADERS[1],
                row_number,
            )
            load_kw = _validate_excel_value_range(
                _parse_excel_float(schema_values[2], STANDARD_XLSX_HEADERS[2], row_number),
                STANDARD_XLSX_HEADERS[2],
                row_number,
            )
            temperature = _parse_excel_float(schema_values[3], STANDARD_XLSX_HEADERS[3], row_number)
            wind_speed = _validate_excel_value_range(
                _parse_excel_float(schema_values[4], STANDARD_XLSX_HEADERS[4], row_number),
                STANDARD_XLSX_HEADERS[4],
                row_number,
            )
            cloud_cover = _validate_excel_value_range(
                _parse_excel_float(schema_values[5], STANDARD_XLSX_HEADERS[5], row_number),
                STANDARD_XLSX_HEADERS[5],
                row_number,
            )

            records.append(
                {
                    "record_time": record_time,
                    "price_kwh": price_kwh,
                    "generation_kwh": 0.0,
                    "load_kw": load_kw,
                    "temperature": temperature,
                    "wind_speed": wind_speed,
                    "cloud_cover": cloud_cover,
                    "weather_type": _derive_weather_type(cloud_cover),
                    "is_holiday": False,
                }
            )

        if not records:
            raise ValueError("Excel文件至少需要包含一行有效数据")
        return records
    finally:
        workbook.close()


def parse_csv_file(file_content: bytes) -> List[Dict[str, Any]]:
    text = None
    for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
        try:
            text = file_content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("无法解码CSV文件，请使用UTF-8或GBK编码")

    reader = csv.reader(StringIO(text))
    rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV文件至少需要包含表头和一行数据")

    headers = [h.strip().lower() for h in rows[0]]
    records = []

    for row in rows[1:]:
        if not any(row):
            continue

        record = {}
        for col_idx, cell in enumerate(row):
            if col_idx >= len(headers):
                continue

            header = headers[col_idx]
            cell = cell.strip() if cell else ""

            if "时间" in header or "time" in header or "date" in header:
                for fmt in TIME_FORMATS:
                    try:
                        record["record_time"] = datetime.strptime(cell, fmt)
                        break
                    except ValueError:
                        continue
            elif "电价" in header or "price" in header:
                record["price_kwh"] = float(cell) if cell else 0.0
            elif "发电" in header or "generation" in header:
                record["generation_kwh"] = float(cell) if cell else 0.0
            elif "负荷" in header or "load" in header:
                record["load_kw"] = float(cell) if cell else 0.0
            elif "天气" in header or "weather" in header:
                record["weather_type"] = cell if cell else "unknown"
            elif "节假日" in header or "holiday" in header:
                record["is_holiday"] = cell.lower() in ("是", "yes", "true", "1") if cell else False

        if record.get("record_time"):
            records.append(record)

    return records


def validate_excel_structure(file_content: bytes) -> tuple[bool, str]:
    try:
        parse_excel_file(file_content)
        return True, ""
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"解析Excel文件失败: {str(exc)}"
