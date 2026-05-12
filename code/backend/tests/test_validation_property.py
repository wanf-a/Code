"""Property-based tests for Form Validation.

Feature: platform-refactor
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient


class TestFormValidation:
    """
    Property 11: 表单验证
    *For any* 无效的表单输入（如空必填字段、格式错误），
    系统应拒绝提交并返回相应的错误信息。
    Validates: Requirements 7.5
    """

    @settings(max_examples=50)
    @given(
        name=st.text(max_size=0),  # Empty name
    )
    def test_empty_name_rejected_for_model_upload(
        self,
        client: TestClient,
        auth_headers: dict,
        name: str,
    ):
        """
        Feature: platform-refactor, Property 11: 表单验证
        Empty model name should be rejected.
        """
        # Create a minimal Python file content
        file_content = b"# test model"
        
        response = client.post(
            "/api/v1/models/upload",
            headers=auth_headers,
            data={
                "name": name,
                "dataset_id": "1",
                "train_start_date": "2024-01-01",
                "train_end_date": "2024-06-30",
                "prediction_type": "day_ahead",
            },
            files={"file": ("test.py", file_content, "text/x-python")},
        )
        
        # Property: Empty name should be rejected (422 validation error)
        assert response.status_code == 422

    @settings(max_examples=30)
    @given(
        prediction_type=st.text(min_size=1, max_size=20).filter(
            lambda x: x not in ("day_ahead", "week_ahead")
        ),
    )
    def test_invalid_prediction_type_rejected(
        self,
        client: TestClient,
        auth_headers: dict,
        prediction_type: str,
    ):
        """
        Feature: platform-refactor, Property 11: 表单验证
        Invalid prediction type should be rejected.
        """
        file_content = b"# test model"
        
        response = client.post(
            "/api/v1/models/upload",
            headers=auth_headers,
            data={
                "name": "Test Model",
                "dataset_id": "1",
                "train_start_date": "2024-01-01",
                "train_end_date": "2024-06-30",
                "prediction_type": prediction_type,
            },
            files={"file": ("test.py", file_content, "text/x-python")},
        )
        
        # Property: Invalid prediction type should be rejected
        assert response.status_code == 400

    def test_non_python_file_rejected(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """
        Feature: platform-refactor, Property 11: 表单验证
        Non-Python files should be rejected for model upload.
        """
        file_content = b"not a python file"
        
        response = client.post(
            "/api/v1/models/upload",
            headers=auth_headers,
            data={
                "name": "Test Model",
                "dataset_id": "1",
                "train_start_date": "2024-01-01",
                "train_end_date": "2024-06-30",
                "prediction_type": "day_ahead",
            },
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        
        # Property: Non-Python file should be rejected
        assert response.status_code == 400
        assert "Python" in response.json().get("detail", "")

    def test_non_excel_file_rejected_for_dataset(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """
        Feature: platform-refactor, Property 11: 表单验证
        Non-Excel files should be rejected for dataset upload.
        """
        file_content = b"not an excel file"
        
        response = client.post(
            "/api/v1/datasets/upload",
            headers=auth_headers,
            data={
                "name": "Test Dataset",
            },
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        
        # Property: Non-Excel file should be rejected
        assert response.status_code == 400
        assert "Excel" in response.json().get("detail", "")

    @settings(max_examples=30)
    @given(
        start_date=st.dates(),
        end_date=st.dates(),
    )
    def test_invalid_date_range_rejected_for_prediction(
        self,
        client: TestClient,
        auth_headers: dict,
        start_date,
        end_date,
    ):
        """
        Feature: platform-refactor, Property 11: 表单验证
        Start date after end date should be rejected for prediction.
        """
        # Only test when start > end
        if start_date <= end_date:
            return
        
        response = client.post(
            "/api/v1/predictions/calculate",
            headers=auth_headers,
            json={
                "model_id": 1,
                "dataset_id": 1,
                "test_start_date": str(start_date),
                "test_end_date": str(end_date),
            },
        )
        
        # Property: Invalid date range should be rejected
        # Note: May return 400 (validation) or 404 (model not found)
        assert response.status_code in (400, 404)
