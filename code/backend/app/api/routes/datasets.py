from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.base_price_data import BasePriceData
from app.models.dataset import Dataset
from app.models.dataset_file import DatasetFile
from app.models.dataset_record import DatasetRecord
from app.schemas.common import Paginated
from app.schemas.dataset import DatasetCreate, DatasetOut, DatasetUpdate
from app.services.excel_service import parse_excel_file, validate_excel_structure
from app.services.storage_service import delete_file, save_upload_file

from app.utils.pagination import paginate

router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASET_RECORD_INSERT_BATCH_SIZE = 5000
VERIFY_STATUS_PENDING = "\u672a\u6821\u6838"
VERIFY_STATUS_RUNNING = "\u6821\u6838\u4e2d"
VERIFY_STATUS_PASSED = "\u6821\u6838\u901a\u8fc7"
VERIFY_STATUS_FAILED = "\u6821\u6838\u5931\u8d25"


def _round_half_up(value: object, digits: int = 2) -> float:
    quantize_pattern = "1" if digits == 0 else f"1.{'0' * digits}"
    decimal_value = Decimal(str(value if value is not None else 0))
    return float(decimal_value.quantize(Decimal(quantize_pattern), rounding=ROUND_HALF_UP))


def _validate_dataset_name(name: str) -> str:
    """验证数据集名称，允许任意非空名称"""
    normalized = (name or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="数据集名称不能为空",
        )
    if len(normalized) > 100:
        raise HTTPException(
            status_code=400,
            detail="数据集名称长度不能超过 100 个字符",
        )
    return normalized


@router.get("", response_model=Paginated[DatasetOut])
def list_datasets(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[DatasetOut]:
    query = db.query(Dataset)
    if keyword:
        query = query.filter(Dataset.name.contains(keyword))
    total, items = paginate(query.order_by(Dataset.id.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.post("", response_model=DatasetOut)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> Dataset:
    name = _validate_dataset_name(payload.name)
    existing_dataset = db.query(Dataset).filter(Dataset.name == name).first()
    if existing_dataset:
        raise HTTPException(status_code=400, detail="数据集名称已存在")

    dataset = Dataset(
        name=name,
        description=payload.description,
        created_by=current_admin.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def compare_records(new_records: list, existing_records: list) -> bool:
    """
    对比上传的数据与已有数据是否相同。
    相同返回True，不同返回False。
    """
    if len(new_records) != len(existing_records):
        return False
    
    # 按时间排序后逐条对比
    new_sorted = sorted(new_records, key=lambda x: x.get("record_time") or "")
    existing_sorted = sorted(existing_records, key=lambda x: x.record_time)
    
    for new_rec, existing_rec in zip(new_sorted, existing_sorted):
        new_time = new_rec.get("record_time")
        new_price = float(new_rec.get("price_kwh", 0) or 0)
        
        if new_time != existing_rec.record_time:
            return False
        if abs(new_price - float(existing_rec.price_kwh or 0)) > 0.001:
            return False
    
    return True


def _normalize_record(record: DatasetRecord) -> tuple:
    return (
        record.record_time,
        _round_half_up(record.price_kwh or 0, 2),
        _round_half_up(record.generation_kwh or 0, 2),
        _round_half_up(record.load_kw or 0, 2),
        record.weather_type or "",
        _round_half_up(record.temperature or 0, 2),
        _round_half_up(record.wind_speed or 0, 2),
        _round_half_up(record.cloud_cover or 0, 2),
        int(record.is_holiday or 0),
    )


def _normalize_uploaded_record(record: dict) -> tuple:
    return (
        record.get("record_time"),
        _round_half_up(record.get("price_kwh", 0) or 0, 2),
        _round_half_up(record.get("generation_kwh", 0) or 0, 2),
        _round_half_up(record.get("load_kw", 0) or 0, 2),
        record.get("weather_type") or "",
        _round_half_up(record.get("temperature", 0) or 0, 2),
        _round_half_up(record.get("wind_speed", 0) or 0, 2),
        _round_half_up(record.get("cloud_cover", 0) or 0, 2),
        int(record.get("is_holiday", 0) or 0),
    )


def _normalize_xlsx_record(record: DatasetRecord) -> tuple:
    return (
        record.record_time,
        _round_half_up(record.price_kwh or 0, 2),
        _round_half_up(record.load_kw or 0, 2),
        _round_half_up(record.temperature or 0, 2),
        _round_half_up(record.wind_speed or 0, 2),
        _round_half_up(record.cloud_cover or 0, 2),
    )


def _normalize_uploaded_xlsx_record(record: dict) -> tuple:
    return (
        record.get("record_time"),
        _round_half_up(record.get("price_kwh", 0) or 0, 2),
        _round_half_up(record.get("load_kw", 0) or 0, 2),
        _round_half_up(record.get("temperature", 0) or 0, 2),
        _round_half_up(record.get("wind_speed", 0) or 0, 2),
        _round_half_up(record.get("cloud_cover", 0) or 0, 2),
    )


def _compare_dataset_records(left_records: list[DatasetRecord], right_records: list[DatasetRecord]) -> bool:
    if len(left_records) != len(right_records):
        return False

    left_sorted = sorted(left_records, key=lambda item: item.record_time)
    right_sorted = sorted(right_records, key=lambda item: item.record_time)
    return all(
        _normalize_record(left_record) == _normalize_record(right_record)
        for left_record, right_record in zip(left_sorted, right_sorted)
    )


def _compare_dataset_with_uploaded_records(
    dataset_records: list[DatasetRecord], uploaded_records: list[dict]
) -> bool:
    if len(dataset_records) != len(uploaded_records):
        return False

    dataset_sorted = sorted(dataset_records, key=lambda item: item.record_time)
    uploaded_sorted = sorted(uploaded_records, key=lambda item: item.get("record_time"))
    return all(
        _normalize_xlsx_record(dataset_record) == _normalize_uploaded_xlsx_record(uploaded_record)
        for dataset_record, uploaded_record in zip(dataset_sorted, uploaded_sorted)
    )


def _find_uploaded_compare_mismatch(
    dataset_records: list[DatasetRecord], uploaded_records: list[dict]
) -> Optional[str]:
    if len(dataset_records) != len(uploaded_records):
        return f"记录条数不一致：数据集1有 {len(dataset_records)} 条，上传文件有 {len(uploaded_records)} 条"

    dataset_sorted = sorted(dataset_records, key=lambda item: item.record_time)
    uploaded_sorted = sorted(uploaded_records, key=lambda item: item.get("record_time"))
    field_labels = ["时间", "电价", "负荷", "温度", "风速", "云量"]

    for index, (dataset_record, uploaded_record) in enumerate(zip(dataset_sorted, uploaded_sorted), start=1):
        dataset_values = _normalize_xlsx_record(dataset_record)
        uploaded_values = _normalize_uploaded_xlsx_record(uploaded_record)
        if dataset_values == uploaded_values:
            continue

        for field_index, (left_value, right_value) in enumerate(zip(dataset_values, uploaded_values)):
            if left_value != right_value:
                return (
                    f"第 {index} 条记录的{field_labels[field_index]}不一致："
                    f"数据集1={left_value}，上传文件={right_value}"
                )

    return "存在未识别的数据差异"


@router.post("/upload", response_model=DatasetOut)
def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> Dataset:
    """按任务一要求上传严格模板Excel数据集。"""
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="只支持Excel文件(.xlsx)")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    normalized_name = _validate_dataset_name(name)
    existing_dataset = db.query(Dataset).filter(Dataset.name == normalized_name).first()
    if existing_dataset:
        raise HTTPException(status_code=400, detail="数据集名称已存在")

    try:
        new_records = parse_excel_file(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset = Dataset(
        name=normalized_name,
        description=description,
        verify_status="未校核",
        created_by=current_admin.id,
    )
    db.add(dataset)
    db.flush()

    _, stored_path = save_upload_file(content, file.filename)
    size_kb = round(len(content) / 1024, 2)
    db.add(
        DatasetFile(
            dataset_id=dataset.id,
            original_name=file.filename,
            stored_path=stored_path,
            size_kb=size_kb,
            description=description,
            created_by=current_admin.id,
        )
    )

    record_mappings = []
    for record_data in new_records:
        record_mappings.append(
            {
                "dataset_id": dataset.id,
                "record_time": record_data["record_time"],
                "price_kwh": record_data["price_kwh"],
                "generation_kwh": record_data.get("generation_kwh", 0.0),
                "load_kw": record_data["load_kw"],
                "weather_type": record_data.get("weather_type", "unknown"),
                "temperature": record_data["temperature"],
                "wind_speed": record_data["wind_speed"],
                "cloud_cover": record_data["cloud_cover"],
                "is_holiday": int(record_data.get("is_holiday", False)),
            }
        )
        if len(record_mappings) >= DATASET_RECORD_INSERT_BATCH_SIZE:
            db.bulk_insert_mappings(DatasetRecord, record_mappings)
            record_mappings.clear()

    if record_mappings:
        db.bulk_insert_mappings(DatasetRecord, record_mappings)

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(stored_path)
        raise

    db.refresh(dataset)
    return dataset


def _verify_dataset_internal(db: Session, dataset_id: int) -> tuple[Dataset, Optional[str]]:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        return None, "数据集不存在"  # type: ignore[return-value]

    uploaded_records = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id
    ).order_by(DatasetRecord.record_time).all()

    if not uploaded_records:
        return dataset, "数据集没有记录，无法校核"

    base_records = db.query(BasePriceData).order_by(BasePriceData.record_time).all()
    if not base_records:
        return dataset, "基础数据不存在，无法校核"

    base_data_map = {}
    for r in base_records:
        base_data_map[r.record_time] = {
            "price_kwh": float(r.price_kwh) if r.price_kwh else 0.0,
            "load_kw": float(r.load_kw) if r.load_kw else 0.0,
        }

    is_match = True
    for record in uploaded_records:
        base_data = base_data_map.get(record.record_time)
        if base_data is None:
            is_match = False
            break
        if abs(float(record.price_kwh or 0) - base_data["price_kwh"]) > 0.01:
            is_match = False
            break
        if abs(float(record.load_kw or 0) - base_data["load_kw"]) > 0.01:
            is_match = False
            break

    dataset.verify_status = VERIFY_STATUS_PASSED if is_match else VERIFY_STATUS_FAILED
    db.commit()
    db.refresh(dataset)
    return dataset, None


def _verify_dataset_background(dataset_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        dataset, err = _verify_dataset_internal(db, dataset_id)
        if err and dataset:
            dataset.verify_status = VERIFY_STATUS_FAILED
            db.commit()
    except Exception:
        db.rollback()
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            dataset.verify_status = VERIFY_STATUS_FAILED
            db.commit()
    finally:
        db.close()


@router.post("/{dataset_id}/verify", response_model=DatasetOut)
def verify_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    """
    同步校核数据集。
    """
    dataset, err = _verify_dataset_internal(db, dataset_id)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return dataset


@router.post("/{dataset_id}/verify-async", response_model=DatasetOut)
def verify_dataset_async(
    dataset_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    dataset.verify_status = VERIFY_STATUS_RUNNING
    db.commit()
    db.refresh(dataset)
    background.add_task(_verify_dataset_background, dataset_id)
    return dataset


@router.post("/{dataset_id}/compare", response_model=DatasetOut)
def compare_dataset(
    dataset_id: int,
    target_dataset_id: int = Form(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    source_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not source_dataset:
        raise HTTPException(status_code=404, detail="鏁版嵁闆嗕笉瀛樺湪")

    target_dataset = db.query(Dataset).filter(Dataset.id == target_dataset_id).first()
    if not target_dataset:
        raise HTTPException(status_code=404, detail="瀵规瘮鏁版嵁闆嗕笉瀛樺湪")

    source_records = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).all()
    if not source_records:
        raise HTTPException(status_code=400, detail="鏁版嵁闆?1 娌℃湁璁板綍锛屾棤娉曟牎鏍?")

    target_records = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == target_dataset_id).all()
    if not target_records:
        raise HTTPException(status_code=400, detail="鏁版嵁闆?2 娌℃湁璁板綍锛屾棤娉曟牎鏍?")

    source_dataset.verify_status = (
        VERIFY_STATUS_PASSED if _compare_dataset_records(source_records, target_records) else VERIFY_STATUS_FAILED
    )
    db.commit()
    db.refresh(source_dataset)
    return source_dataset


@router.post("/{dataset_id}/compare-upload", response_model=DatasetOut)
def compare_dataset_with_upload(
    dataset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    source_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not source_dataset:
        raise HTTPException(status_code=404, detail="鏁版嵁闆嗕笉瀛樺湪")

    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="鍙敮鎸?xlsx 鏂囦欢")

    source_records = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).all()
    if not source_records:
        raise HTTPException(status_code=400, detail="鏁版嵁闆?1 娌℃湁璁板綍锛屾棤娉曟牎鏍?")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="涓婁紶鐨勬枃浠朵负绌?")

    try:
        uploaded_records = parse_excel_file(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    is_match = _compare_dataset_with_uploaded_records(source_records, uploaded_records)
    source_dataset.verify_status = VERIFY_STATUS_PASSED if is_match else VERIFY_STATUS_FAILED
    db.commit()
    db.refresh(source_dataset)
    if not is_match:
        mismatch_detail = _find_uploaded_compare_mismatch(source_records, uploaded_records)
        raise HTTPException(status_code=400, detail=mismatch_detail or "校核失败")
    return source_dataset


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> FileResponse:
    """下载数据集的原始 Excel 文件"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 获取关联的文件
    db_file = db.query(DatasetFile).filter(DatasetFile.dataset_id == dataset_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="数据集文件不存在")
    
    if not os.path.exists(db_file.stored_path):
        raise HTTPException(status_code=404, detail="文件已丢失")
    
    return FileResponse(db_file.stored_path, filename=db_file.original_name)


@router.put("/{dataset_id}", response_model=DatasetOut)
def update_dataset(
    dataset_id: int,
    payload: DatasetUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    normalized_name = _validate_dataset_name(payload.name)
    existing_dataset = (
        db.query(Dataset)
        .filter(Dataset.name == normalized_name, Dataset.id != dataset_id)
        .first()
    )
    if existing_dataset:
        raise HTTPException(status_code=400, detail="数据集名称已存在")

    dataset.name = normalized_name
    dataset.description = payload.description
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 删除关联的文件
    db_files = db.query(DatasetFile).filter(DatasetFile.dataset_id == dataset_id).all()
    for db_file in db_files:
        delete_file(db_file.stored_path)
    
    db.delete(dataset)
    db.commit()
    return {"message": "Deleted"}


@router.post("/upload-csv", response_model=DatasetOut)
def upload_csv_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> Dataset:
    # Legacy compatibility alias: despite the /upload-csv path name, this endpoint
    # now delegates to the xlsx-only upload flow and accepts only .xlsx files.
    return upload_dataset(
        file=file,
        name=name,
        description=description,
        db=db,
        current_admin=current_admin,
    )
