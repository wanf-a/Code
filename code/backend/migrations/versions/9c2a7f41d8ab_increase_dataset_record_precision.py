"""Increase dataset record precision for task1 raw row display

Revision ID: 9c2a7f41d8ab
Revises: 4f3b9a2b0b7a
Create Date: 2026-05-09 13:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "9c2a7f41d8ab"
down_revision = "4f3b9a2b0b7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("dataset_record", "price_kwh", existing_type=sa.Numeric(12, 2), type_=sa.Numeric(12, 4), existing_nullable=False)
    op.alter_column("dataset_record", "load_kw", existing_type=sa.Numeric(12, 2), type_=sa.Numeric(12, 4), existing_nullable=False)
    op.alter_column("dataset_record", "temperature", existing_type=sa.Numeric(8, 2), type_=sa.Numeric(8, 4), existing_nullable=True)
    op.alter_column("dataset_record", "wind_speed", existing_type=sa.Numeric(8, 2), type_=sa.Numeric(8, 4), existing_nullable=True)
    op.alter_column("dataset_record", "cloud_cover", existing_type=sa.Numeric(8, 2), type_=sa.Numeric(8, 4), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("dataset_record", "cloud_cover", existing_type=sa.Numeric(8, 4), type_=sa.Numeric(8, 2), existing_nullable=True)
    op.alter_column("dataset_record", "wind_speed", existing_type=sa.Numeric(8, 4), type_=sa.Numeric(8, 2), existing_nullable=True)
    op.alter_column("dataset_record", "temperature", existing_type=sa.Numeric(8, 4), type_=sa.Numeric(8, 2), existing_nullable=True)
    op.alter_column("dataset_record", "load_kw", existing_type=sa.Numeric(12, 4), type_=sa.Numeric(12, 2), existing_nullable=False)
    op.alter_column("dataset_record", "price_kwh", existing_type=sa.Numeric(12, 4), type_=sa.Numeric(12, 2), existing_nullable=False)
