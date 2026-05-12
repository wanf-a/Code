from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.deps import get_db
from app.models.task import Task
from app.models.task_log import TaskLog
from app.schemas.common import Paginated
from app.schemas.task import TaskCreate, TaskOut, TaskLogOut
from app.services.task_service import execute_task
from app.utils.pagination import paginate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Paginated[TaskOut])
def list_tasks(
    page: int = 1,
    size: int = 20,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[TaskOut]:
    query = db.query(Task)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    total, items = paginate(query.order_by(Task.created_at.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> TaskOut:
    try:
        json.loads(payload.payload_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="payload_json must be valid JSON")

    task = Task(
        task_type=payload.task_type,
        payload_json=payload.payload_json,
        max_retries=payload.max_retries,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background.add_task(_execute_task_background, task.id)
    return task


def _execute_task_background(task_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            execute_task(db, task)
    finally:
        db.close()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> TaskOut:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/logs", response_model=Paginated[TaskLogOut])
def get_task_logs(
    task_id: int,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> Paginated[TaskLogOut]:
    query = db.query(TaskLog).filter(TaskLog.task_id == task_id)
    total, items = paginate(query.order_by(TaskLog.created_at.desc()), page, size)
    return Paginated(total=total, items=items, page=page, size=size)
