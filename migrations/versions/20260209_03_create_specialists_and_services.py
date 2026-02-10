"""create specialist profiles and services

Revision ID: 20260209_03
Revises: 20260209_02
Create Date: 2026-02-09 19:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260209_03"
down_revision: Union[str, None] = "20260209_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "specialist_profiles",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_specialist_profiles_user_id"),
    )
    op.create_index("ix_specialist_profiles_id", "specialist_profiles", ["id"], unique=False)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialist_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_services_id", "services", ["id"], unique=False)
    op.create_index("ix_services_specialist_id", "services", ["specialist_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_services_specialist_id", table_name="services")
    op.drop_index("ix_services_id", table_name="services")
    op.drop_table("services")

    op.drop_index("ix_specialist_profiles_id", table_name="specialist_profiles")
    op.drop_table("specialist_profiles")
