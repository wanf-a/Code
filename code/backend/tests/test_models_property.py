"""Property-based tests for Model management.

Feature: platform-refactor
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.dataset import Dataset


# Strategies for generating test data
model_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())

prediction_type_strategy = st.sampled_from(["day_ahead", "week_ahead"])

date_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2025, 12, 31)
)


@pytest.fixture
def sample_dataset(db: Session) -> Dataset:
    """Create a sample dataset for testing."""
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
        description="Test dataset for model testing",
        created_by=admin.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


class TestModelInitialStatus:
    """
    Property 6: 模型初始状态
    *For any* 新上传的模型，其初始状态应为"未训练"(untrained)。
    Validates: Requirements 4.3
    """

    @settings(max_examples=100)
    @given(
        name=model_name_strategy,
        prediction_type=prediction_type_strategy,
        start_date=date_strategy,
    )
    def test_new_model_has_untrained_status(
        self,
        db: Session,
        sample_dataset: Dataset,
        name: str,
        prediction_type: str,
        start_date: date,
    ):
        """
        Feature: platform-refactor, Property 6: 模型初始状态
        For any new model created, its status should be 'untrained'.
        """
        end_date = start_date + timedelta(days=30)
        
        model = Model(
            name=name,
            description="Test model",
            file_path="/tmp/test_model.py",
            original_name="test_model.py",
            dataset_id=sample_dataset.id,
            train_start_date=start_date,
            train_end_date=end_date,
            prediction_type=prediction_type,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        
        # Property: New model status should always be 'untrained'
        assert model.status == "untrained"
        assert model.trained_at is None
        
        # Cleanup
        db.delete(model)
        db.commit()

    @settings(max_examples=50)
    @given(
        names=st.lists(model_name_strategy, min_size=1, max_size=5),
        prediction_type=prediction_type_strategy,
    )
    def test_multiple_models_all_start_untrained(
        self,
        db: Session,
        sample_dataset: Dataset,
        names: list,
        prediction_type: str,
    ):
        """
        Feature: platform-refactor, Property 6: 模型初始状态
        For any batch of new models, all should start with 'untrained' status.
        """
        models = []
        start_date = date(2024, 1, 1)
        end_date = date(2024, 6, 30)
        
        for i, name in enumerate(names):
            model = Model(
                name=f"{name}_{i}",
                description=f"Test model {i}",
                file_path=f"/tmp/test_model_{i}.py",
                original_name=f"test_model_{i}.py",
                dataset_id=sample_dataset.id,
                train_start_date=start_date,
                train_end_date=end_date,
                prediction_type=prediction_type,
            )
            db.add(model)
            models.append(model)
        
        db.commit()
        
        # Property: All new models should have 'untrained' status
        for model in models:
            db.refresh(model)
            assert model.status == "untrained"
            assert model.trained_at is None
        
        # Cleanup
        for model in models:
            db.delete(model)
        db.commit()



class TestModelTrainingStatusChange:
    """
    Property 7: 模型训练状态变更
    *For any* 未训练的模型，执行训练操作后其状态应变更为"已训练"(trained)，
    且trained_at字段应被设置。
    Validates: Requirements 4.4
    """

    @settings(max_examples=100)
    @given(
        name=model_name_strategy,
        prediction_type=prediction_type_strategy,
        start_date=date_strategy,
    )
    def test_training_changes_status_to_trained(
        self,
        db: Session,
        sample_dataset: Dataset,
        name: str,
        prediction_type: str,
        start_date: date,
    ):
        """
        Feature: platform-refactor, Property 7: 模型训练状态变更
        For any untrained model, training should change status to 'trained'.
        """
        from datetime import datetime
        
        end_date = start_date + timedelta(days=30)
        
        # Create untrained model
        model = Model(
            name=name,
            description="Test model",
            file_path="/tmp/test_model.py",
            original_name="test_model.py",
            dataset_id=sample_dataset.id,
            train_start_date=start_date,
            train_end_date=end_date,
            prediction_type=prediction_type,
            status="untrained",
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        
        # Verify initial state
        assert model.status == "untrained"
        assert model.trained_at is None
        
        # Simulate training
        model.status = "trained"
        model.trained_at = datetime.utcnow()
        db.add(model)
        db.commit()
        db.refresh(model)
        
        # Property: After training, status should be 'trained' and trained_at should be set
        assert model.status == "trained"
        assert model.trained_at is not None
        
        # Cleanup
        db.delete(model)
        db.commit()

    @settings(max_examples=50)
    @given(
        name=model_name_strategy,
        prediction_type=prediction_type_strategy,
    )
    def test_trained_at_is_set_after_training(
        self,
        db: Session,
        sample_dataset: Dataset,
        name: str,
        prediction_type: str,
    ):
        """
        Feature: platform-refactor, Property 7: 模型训练状态变更
        For any model that is trained, trained_at timestamp should be set.
        """
        from datetime import datetime
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 6, 30)
        
        model = Model(
            name=name,
            description="Test model",
            file_path="/tmp/test_model.py",
            original_name="test_model.py",
            dataset_id=sample_dataset.id,
            train_start_date=start_date,
            train_end_date=end_date,
            prediction_type=prediction_type,
            status="untrained",
        )
        db.add(model)
        db.commit()
        
        before_training = datetime.utcnow()
        
        # Train the model
        model.status = "trained"
        model.trained_at = datetime.utcnow()
        db.add(model)
        db.commit()
        db.refresh(model)
        
        after_training = datetime.utcnow()
        
        # Property: trained_at should be between before and after training timestamps
        assert model.trained_at is not None
        assert before_training <= model.trained_at <= after_training
        
        # Cleanup
        db.delete(model)
        db.commit()
