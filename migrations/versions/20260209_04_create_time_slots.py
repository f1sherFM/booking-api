"""create time slots

Revision ID: 20260209_04
Revises: 20260209_03
Create Date: 2026-02-09 19:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260209_04"
down_revision: Union[str, None] = "20260209_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "time_slots",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialist_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_time_slots_id", "time_slots", ["id"], unique=False)
    op.create_index("ix_time_slots_specialist_id", "time_slots", ["specialist_id"], unique=False)
    op.create_index("ix_time_slots_start_at", "time_slots", ["start_at"], unique=False)
    op.create_index("ix_time_slots_end_at", "time_slots", ["end_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_time_slots_end_at", table_name="time_slots")
    op.drop_index("ix_time_slots_start_at", table_name="time_slots")
    op.drop_index("ix_time_slots_specialist_id", table_name="time_slots")
    op.drop_index("ix_time_slots_id", table_name="time_slots")
    op.drop_table("time_slots")
