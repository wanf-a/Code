from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.admin import AdminUser
from app.models.dataset import Dataset
from app.models.dataset_file import DatasetFile
from app.models.dataset_record import DatasetRecord
from app.models.plan import Plan
from app.models.plan_result import PlanResult
from app.models.ranking import Ranking


WEATHER_TYPES = ["晴天", "阴天", "雨天"]


def seed_demo_data(db: Session) -> None:
    if db.query(AdminUser).first():
        return

    admin = AdminUser(
        username="admin",
        display_name="admin",
        password_hash=get_password_hash("admin123"),
    )
    db.add(admin)
    db.flush()

    dataset = Dataset(
        name="电价数据-导入",
        description="电价数据导入",
        created_by=admin.id,
    )
    db.add(dataset)
    db.flush()

    sample_file = DatasetFile(
        dataset_id=dataset.id,
        original_name="NSW电价预测需求大模型.csv",
        stored_path="storage/uploads/sample.csv",
        size_kb=2820.35,
        description="电价数据导入",
        created_by=admin.id,
    )
    db.add(sample_file)

    base_time = datetime(2016, 12, 31, 23, 0, 0)
    for idx in range(24):
        record_time = base_time - timedelta(hours=idx)
        record = DatasetRecord(
            dataset_id=dataset.id,
            record_time=record_time,
            price_kwh=60.0 - idx * 0.6,
            generation_kwh=66000 + idx * 120,
            load_kw=72000 - idx * 140,
            weather_type=WEATHER_TYPES[0],
            is_holiday=0,
        )
        db.add(record)

    plan = Plan(
        name="测试电价预测",
        plan_type="电价预测",
        dataset_id=dataset.id,
        status="已完成",
        description="",
        created_by=admin.id,
    )
    db.add(plan)
    db.flush()

    results = [
        PlanResult(
            plan_id=plan.id,
            model_name="CS",
            weather="全天",
            mae=56.335,
            nmae=1.846,
            rmse=57.783,
            nrmse=1.894,
            score=-93.186,
        ),
        PlanResult(
            plan_id=plan.id,
            model_name="测试linux",
            weather="全天",
            mae=4.906,
            nmae=0.161,
            rmse=5.934,
            nrmse=0.194,
            score=81.803,
        ),
    ]
    db.add_all(results)

    ranking = Ranking(
        score=80,
        time_range="2016-05-31 - 2016-05-31",
        mae_ratio=0.5,
        rmse_ratio=0.5,
        rank_type="电价日",
        weather="晴天",
        is_holiday=0,
        model_name="电价日预测模型",
        author="admin",
        plan_id=plan.id,
        created_at=datetime.utcnow(),
    )
    db.add(ranking)

    db.commit()

