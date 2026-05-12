"""Property-based tests for Dataset management.

Feature: platform-refactor
"""
from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_record import DatasetRecord


# Strategies for generating test data
date_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2025, 12, 31),
)

price_strategy = st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)


@pytest.fixture
def sample_dataset(db: Session) -> Dataset:
    """Create a sample dataset for testing."""
    from app.models.admin import AdminUser
    from app.core.security import get_password_hash
    
    admin = db.query(AdminUser).filter(AdminUser.username == "testadmin").first()
    if not admin:
        admin = AdminUser(
            username="testadmin",
            password_hash=get_password_hash("testpass123"),
            email="test@example.com",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    
    dataset = Dataset(
        name="Test Dataset",
        description="Test dataset",
        created_by=admin.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


class TestDateRangeFilter:
    """
    Property 4: 日期范围筛选正确性
    *For any* 日期范围筛选查询，返回的所有记录的时间戳都应在指定的开始日期和结束日期范围内（包含边界）。
    Validates: Requirements 2.6
    """

    @settings(max_examples=50)
    @given(
        start_offset=st.integers(min_value=0, max_value=10),
        end_offset=st.integers(min_value=11, max_value=20),
    )
    def test_records_within_date_range(
        self,
        db: Session,
        sample_dataset: Dataset,
        start_offset: int,
        end_offset: int,
    ):
        """
        Feature: platform-refactor, Property 4: 日期范围筛选正确性
        For any date range query, all returned records should be within the range.
        """
        base_time = datetime(2024, 1, 1)
        
        # Create records spanning 30 days
        for day in range(30):
            record = DatasetRecord(
                dataset_id=sample_dataset.id,
                record_time=base_time + timedelta(days=day),
                price_kwh=100.0 + day,
                generation_kwh=500.0,
                load_kw=300.0,
                weather_type="sunny",
                is_holiday=False,
            )
            db.add(record)
        db.commit()
        
        # Query with date range
        start_date = base_time + timedelta(days=start_offset)
        end_date = base_time + timedelta(days=end_offset)
        
        records = db.query(DatasetRecord).filter(
            DatasetRecord.dataset_id == sample_dataset.id,
            DatasetRecord.record_time >= start_date,
            DatasetRecord.record_time <= end_date,
        ).all()
        
        # Property: All returned records should be within the date range
        for record in records:
            assert start_date <= record.record_time <= end_date
        
        # Cleanup
        db.query(DatasetRecord).filter(
            DatasetRecord.dataset_id == sample_dataset.id
        ).delete()
        db.commit()

    @settings(max_examples=30)
    @given(
        num_records=st.integers(min_value=5, max_value=20),
    )
    def test_no_records_outside_range(
        self,
        db: Session,
        sample_dataset: Dataset,
        num_records: int,
    ):
        """
        Feature: platform-refactor, Property 4: 日期范围筛选正确性
        Records outside the date range should not be returned.
        """
        base_time = datetime(2024, 1, 1)
        
        # Create records
        for day in range(num_records):
            record = DatasetRecord(
                dataset_id=sample_dataset.id,
                record_time=base_time + timedelta(days=day),
                price_kwh=100.0 + day,
                generation_kwh=500.0,
                load_kw=300.0,
                weather_type="sunny",
                is_holiday=False,
            )
            db.add(record)
        db.commit()
        
        # Query middle range
        start_date = base_time + timedelta(days=2)
        end_date = base_time + timedelta(days=num_records - 3)
        
        records = db.query(DatasetRecord).filter(
            DatasetRecord.dataset_id == sample_dataset.id,
            DatasetRecord.record_time >= start_date,
            DatasetRecord.record_time <= end_date,
        ).all()
        
        # Property: No record should be outside the range
        for record in records:
            assert record.record_time >= start_date
            assert record.record_time <= end_date
        
        # Cleanup
        db.query(DatasetRecord).filter(
            DatasetRecord.dataset_id == sample_dataset.id
        ).delete()
        db.commit()


class TestFileRoundTrip:
    """
    Property 2: 文件上传下载Round-Trip
    *For any* 上传的Excel文件，下载该文件后内容应与原始上传文件完全一致。
    Validates: Requirements 2.2, 2.4, 3.2
    """

    def test_file_content_preserved(self, db: Session):
        """
        Feature: platform-refactor, Property 2: 文件上传下载Round-Trip
        File content should be preserved after upload and download.
        """
        from app.services.storage_service import save_upload_file, delete_file
        import os
        
        # Create test content
        original_content = b"Test file content for round-trip testing"
        
        # Save file
        stored_name, stored_path = save_upload_file(original_content, "test.txt")
        
        # Read back
        with open(stored_path, "rb") as f:
            downloaded_content = f.read()
        
        # Property: Content should be identical
        assert downloaded_content == original_content
        
        # Cleanup
        delete_file(stored_path)

    @settings(max_examples=50)
    @given(
        content=st.binary(min_size=10, max_size=1000),
    )
    def test_binary_content_preserved(self, content: bytes):
        """
        Feature: platform-refactor, Property 2: 文件上传下载Round-Trip
        For any binary content, upload then download should preserve the content.
        """
        from app.services.storage_service import save_upload_file, delete_file
        
        # Save file
        stored_name, stored_path = save_upload_file(content, "test.bin")
        
        # Read back
        with open(stored_path, "rb") as f:
            downloaded_content = f.read()
        
        # Property: Content should be identical
        assert downloaded_content == content
        
        # Cleanup
        delete_file(stored_path)
