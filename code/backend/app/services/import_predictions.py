"""导入预测数据CSV到数据库"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.price_prediction import PricePrediction


def import_prediction_csv(csv_path: str) -> int:
    """
    导入预测结果CSV文件到price_prediction表
    
    CSV格式: date, y_test_true, y_test_pred
    """
    db: Session = SessionLocal()
    count = 0
    
    try:
        # 先清空表
        db.query(PricePrediction).delete()
        db.commit()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            
            for row in reader:
                # 解析时间: 2024/3/22 0:15
                date_str = row['date'].strip()
                try:
                    record_time = datetime.strptime(date_str, '%Y/%m/%d %H:%M')
                except ValueError:
                    try:
                        record_time = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                
                actual = float(row['y_test_true']) if row['y_test_true'] else 0
                predicted = float(row['y_test_pred']) if row['y_test_pred'] else 0
                
                record = PricePrediction(
                    record_time=record_time,
                    actual_price=actual,
                    predicted_price=predicted,
                )
                batch.append(record)
                count += 1
                
                # 批量插入
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.commit()
                    batch = []
            
            # 插入剩余数据
            if batch:
                db.add_all(batch)
                db.commit()
                
    finally:
        db.close()
    
    return count


if __name__ == "__main__":
    csv_file = Path(__file__).parent.parent.parent.parent / "广东电价预测结果.csv"
    if csv_file.exists():
        imported = import_prediction_csv(str(csv_file))
        print(f"导入完成: {imported} 条记录")
    else:
        print(f"文件不存在: {csv_file}")
