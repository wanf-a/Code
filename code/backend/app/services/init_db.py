from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import Base, get_engine
from app.models.task import Task
from app.services.seed_service import seed_demo_data
from app.services.import_base_data import import_all_base_data


def _cleanup_stale_tasks(db: Session) -> None:
    stale = db.query(Task).filter(Task.status.in_(["queued", "running"])).all()
    for task in stale:
        task.status = "failed"
        task.last_error = "Marked failed: server restarted while task was running."
        task.finished_at = datetime.utcnow()
        db.add(task)
    if stale:
        db.commit()


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as db:
        seed_demo_data(db)
        import_all_base_data(db)
        _cleanup_stale_tasks(db)

