from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.dataset_file import DatasetFile
from app.schemas.common import Paginated
from app.schemas.dataset_file import DatasetFileOut
from app.services.storage_service import delete_file, save_upload_file
from app.utils.pagination import paginate

router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=Paginated[DatasetFileOut])

def list_files(
    page: int = 1,
    size: int = 20,
    dataset_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[DatasetFileOut]:
    query = db.query(DatasetFile)
    if dataset_id:
        query = query.filter(DatasetFile.dataset_id == dataset_id)
    if keyword:
        query = query.filter(DatasetFile.original_name.contains(keyword))
    total, items = paginate(query.order_by(DatasetFile.id.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.post("/upload", response_model=DatasetFileOut)

def upload_file(
    dataset_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> DatasetFile:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    stored_name, stored_path = save_upload_file(content, file.filename)
    size_kb = round(len(content) / 1024, 2)
    db_file = DatasetFile(
        dataset_id=dataset_id,
        original_name=file.filename,
        stored_path=stored_path,
        size_kb=size_kb,
        description=description,
        created_by=current_admin.id,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


@router.get("/{file_id}/download")

def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> FileResponse:
    db_file = db.query(DatasetFile).filter(DatasetFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.exists(db_file.stored_path):
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(db_file.stored_path, filename=db_file.original_name)


@router.delete("/{file_id}")

def delete_file_item(
    file_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict:
    db_file = db.query(DatasetFile).filter(DatasetFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    delete_file(db_file.stored_path)
    db.delete(db_file)
    db.commit()
    return {"message": "Deleted"}

