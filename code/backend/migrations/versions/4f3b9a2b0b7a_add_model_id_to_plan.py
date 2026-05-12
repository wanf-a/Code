"""Add model_id to plan

Revision ID: 4f3b9a2b0b7a
Revises: b152495d42aa
Create Date: 2026-03-11 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "4f3b9a2b0b7a"
down_revision = "b152495d42aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan", sa.Column("model_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_plan_model_id"), "plan", ["model_id"], unique=False)
    op.create_foreign_key(
        "fk_plan_model_id_model",
        "plan",
        "model",
        ["model_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_plan_model_id_model", "plan", type_="foreignkey")
    op.drop_index(op.f("ix_plan_model_id"), table_name="plan")
    op.drop_column("plan", "model_id")
