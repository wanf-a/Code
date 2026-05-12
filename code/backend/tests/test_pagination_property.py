"""Property-based tests for Pagination.

Feature: platform-refactor
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.utils.pagination import paginate


@pytest.fixture
def sample_datasets(db: Session) -> list[Dataset]:
    """Create sample datasets for pagination testing."""
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
    
    datasets = []
    for i in range(50):
        dataset = Dataset(
            name=f"Dataset {i}",
            description=f"Description {i}",
            created_by=admin.id,
        )
        db.add(dataset)
        datasets.append(dataset)
    
    db.commit()
    return datasets


class TestPaginationProperty:
    """
    Property 10: 分页正确性
    *For any* 分页查询，返回的记录数应不超过请求的page_size，
    且total字段应反映符合条件的总记录数。
    Validates: Requirements 7.4
    """

    @settings(max_examples=50)
    @given(
        page=st.integers(min_value=1, max_value=10),
        size=st.integers(min_value=1, max_value=20),
    )
    def test_pagination_returns_correct_count(
        self,
        db: Session,
        sample_datasets: list[Dataset],
        page: int,
        size: int,
    ):
        """
        Feature: platform-refactor, Property 10: 分页正确性
        For any pagination query, returned items should not exceed page_size.
        """
        query = db.query(Dataset)
        total, items = paginate(query, page, size)
        
        # Property: Returned items should not exceed page_size
        assert len(items) <= size
        
        # Property: Total should reflect actual count
        assert total == len(sample_datasets)

    @settings(max_examples=30)
    @given(
        size=st.integers(min_value=5, max_value=15),
    )
    def test_pagination_total_is_consistent(
        self,
        db: Session,
        sample_datasets: list[Dataset],
        size: int,
    ):
        """
        Feature: platform-refactor, Property 10: 分页正确性
        Total count should be consistent across all pages.
        """
        query = db.query(Dataset)
        
        # Get totals from different pages
        total_page1, _ = paginate(query, 1, size)
        total_page2, _ = paginate(query, 2, size)
        total_page3, _ = paginate(query, 3, size)
        
        # Property: Total should be the same regardless of page
        assert total_page1 == total_page2 == total_page3

    @settings(max_examples=30)
    @given(
        page=st.integers(min_value=1, max_value=5),
        size=st.integers(min_value=5, max_value=20),
    )
    def test_pagination_no_duplicates_across_pages(
        self,
        db: Session,
        sample_datasets: list[Dataset],
        page: int,
        size: int,
    ):
        """
        Feature: platform-refactor, Property 10: 分页正确性
        Items should not appear on multiple pages.
        """
        query = db.query(Dataset).order_by(Dataset.id)
        
        # Get items from consecutive pages
        _, items_page1 = paginate(query, page, size)
        _, items_page2 = paginate(query, page + 1, size)
        
        # Property: No item should appear on both pages
        ids_page1 = {item.id for item in items_page1}
        ids_page2 = {item.id for item in items_page2}
        
        assert ids_page1.isdisjoint(ids_page2)

    def test_pagination_empty_result_for_out_of_range_page(
        self,
        db: Session,
        sample_datasets: list[Dataset],
    ):
        """
        Feature: platform-refactor, Property 10: 分页正确性
        Out of range page should return empty items but correct total.
        """
        query = db.query(Dataset)
        
        # Request page way beyond available data
        total, items = paginate(query, 100, 10)
        
        # Property: Items should be empty for out of range page
        assert len(items) == 0
        
        # Property: Total should still be correct
        assert total == len(sample_datasets)
