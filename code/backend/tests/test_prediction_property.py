"""Property-based tests for Prediction service.

Feature: platform-refactor
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import math

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_record import DatasetRecord
from app.models.model import Model
from app.services.prediction_service import (
    get_base_model_prediction,
    calculate_metrics,
    PredictionMetrics,
)


@pytest.fixture
def sample_dataset_with_records(db: Session) -> tuple[Dataset, list[DatasetRecord]]:
    """Create a sample dataset with records for testing."""
    from app.models.admin import AdminUser
    from app.core.security import get_password_hash
    
    # Create admin user first
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
        description="Test dataset for prediction testing",
        created_by=admin.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Create records for 14 days (to support week_ahead predictions)
    records = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    for day in range(14):
        for hour in range(24):
            record_time = base_time + timedelta(days=day, hours=hour)
            record = DatasetRecord(
                dataset_id=dataset.id,
                record_time=record_time,
                price_kwh=100.0 + day * 10 + hour,  # Predictable pattern
                generation_kwh=500.0,
                load_kw=300.0,
                weather_type="sunny",
                is_holiday=False,
            )
            db.add(record)
            records.append(record)
    
    db.commit()
    return dataset, records


class TestBaseModelPrediction:
    """
    Property 9: Base模型预测逻辑
    *For any* 日前预测，Base模型的预测值应等于前一天同时刻的实际电价值；
    *For any* 周前预测，Base模型的预测值应等于前一周同时刻的实际电价值。
    Validates: Requirements 5.6
    """

    def test_day_ahead_returns_previous_day_value(
        self,
        db: Session,
        sample_dataset_with_records: tuple[Dataset, list[DatasetRecord]],
    ):
        """
        Feature: platform-refactor, Property 9: Base模型预测逻辑
        For day_ahead prediction, should return the value from exactly 1 day ago.
        """
        dataset, records = sample_dataset_with_records
        
        # Test for day 2 (should get day 1 values)
        test_time = datetime(2024, 1, 2, 12, 0, 0)  # Day 2, hour 12
        
        prediction = get_base_model_prediction(
            db, dataset.id, test_time, "day_ahead"
        )
        
        # Expected: Day 1, hour 12 value = 100 + 1*10 + 12 = 122
        expected_value = 100.0 + 1 * 10 + 12
        assert prediction == expected_value

    def test_week_ahead_returns_previous_week_value(
        self,
        db: Session,
        sample_dataset_with_records: tuple[Dataset, list[DatasetRecord]],
    ):
        """
        Feature: platform-refactor, Property 9: Base模型预测逻辑
        For week_ahead prediction, should return the value from exactly 7 days ago.
        """
        dataset, records = sample_dataset_with_records
        
        # Test for day 8 (should get day 1 values)
        test_time = datetime(2024, 1, 8, 12, 0, 0)  # Day 8, hour 12
        
        prediction = get_base_model_prediction(
            db, dataset.id, test_time, "week_ahead"
        )
        
        # Expected: Day 1, hour 12 value = 100 + 1*10 + 12 = 122
        expected_value = 100.0 + 1 * 10 + 12
        assert prediction == expected_value

    @settings(max_examples=50)
    @given(
        day_offset=st.integers(min_value=1, max_value=6),
        hour=st.integers(min_value=0, max_value=23),
    )
    def test_day_ahead_property(
        self,
        db: Session,
        sample_dataset_with_records: tuple[Dataset, list[DatasetRecord]],
        day_offset: int,
        hour: int,
    ):
        """
        Feature: platform-refactor, Property 9: Base模型预测逻辑
        For any day_ahead prediction at time T, the result should equal
        the actual value at time T - 1 day.
        """
        dataset, records = sample_dataset_with_records
        
        # Test time is day_offset + 1 (to ensure we have previous day data)
        test_time = datetime(2024, 1, day_offset + 1, hour, 0, 0)
        
        prediction = get_base_model_prediction(
            db, dataset.id, test_time, "day_ahead"
        )
        
        # Expected value from previous day
        expected_value = 100.0 + day_offset * 10 + hour
        assert prediction == expected_value

    @settings(max_examples=50)
    @given(
        day_offset=st.integers(min_value=7, max_value=13),
        hour=st.integers(min_value=0, max_value=23),
    )
    def test_week_ahead_property(
        self,
        db: Session,
        sample_dataset_with_records: tuple[Dataset, list[DatasetRecord]],
        day_offset: int,
        hour: int,
    ):
        """
        Feature: platform-refactor, Property 9: Base模型预测逻辑
        For any week_ahead prediction at time T, the result should equal
        the actual value at time T - 7 days.
        """
        dataset, records = sample_dataset_with_records
        
        test_time = datetime(2024, 1, day_offset + 1, hour, 0, 0)
        
        prediction = get_base_model_prediction(
            db, dataset.id, test_time, "week_ahead"
        )
        
        # Expected value from 7 days ago
        expected_day = day_offset - 7
        expected_value = 100.0 + expected_day * 10 + hour
        assert prediction == expected_value


class TestPredictionMetrics:
    """
    Property 8: 预测结果完整性
    测试指标计算的正确性。
    Validates: Requirements 5.3, 5.4, 5.5
    """

    @settings(max_examples=100)
    @given(
        values=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        )
    )
    def test_perfect_prediction_has_zero_error(self, values: list[float]):
        """
        Feature: platform-refactor, Property 8: 预测结果完整性
        For any perfect prediction (predicted == actual), MAE and RMSE should be 0.
        """
        metrics = calculate_metrics(values, values)
        
        assert metrics.mae == 0.0
        assert metrics.rmse == 0.0
        assert metrics.accuracy == 100.0

    @settings(max_examples=100)
    @given(
        actual=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        ),
        error=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_mae_is_non_negative(self, actual: list[float], error: float):
        """
        Feature: platform-refactor, Property 8: 预测结果完整性
        MAE should always be non-negative.
        """
        predicted = [v + error for v in actual]
        metrics = calculate_metrics(actual, predicted)
        
        assert metrics.mae >= 0.0

    @settings(max_examples=100)
    @given(
        actual=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        ),
        error=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_rmse_is_non_negative(self, actual: list[float], error: float):
        """
        Feature: platform-refactor, Property 8: 预测结果完整性
        RMSE should always be non-negative.
        """
        predicted = [v + error for v in actual]
        metrics = calculate_metrics(actual, predicted)
        
        assert metrics.rmse >= 0.0

    @settings(max_examples=100)
    @given(
        actual=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        ),
        error=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_rmse_greater_or_equal_mae(self, actual: list[float], error: float):
        """
        Feature: platform-refactor, Property 8: 预测结果完整性
        RMSE should always be >= MAE (mathematical property).
        """
        predicted = [v + error for v in actual]
        metrics = calculate_metrics(actual, predicted)
        
        # RMSE >= MAE is a mathematical property
        assert metrics.rmse >= metrics.mae - 0.0001  # Small tolerance for floating point

    @settings(max_examples=100)
    @given(
        actual=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        ),
    )
    def test_accuracy_in_valid_range(self, actual: list[float]):
        """
        Feature: platform-refactor, Property 8: 预测结果完整性
        Accuracy should be between 0 and 100.
        """
        # Add small random errors
        import random
        predicted = [v * (1 + random.uniform(-0.1, 0.1)) for v in actual]
        metrics = calculate_metrics(actual, predicted)
        
        assert 0.0 <= metrics.accuracy <= 100.0
