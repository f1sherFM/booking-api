"""create bookings

Revision ID: 20260209_05
Revises: 20260209_04
Create Date: 2026-02-09 19:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260209_05"
down_revision: Union[str, None] = "20260209_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="confirmed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["slot_id"], ["time_slots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("slot_id", name="uq_bookings_slot_id"),
    )
    op.create_index("ix_bookings_id", "bookings", ["id"], unique=False)
    op.create_index("ix_bookings_client_id", "bookings", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_client_id", table_name="bookings")
    op.drop_index("ix_bookings_id", table_name="bookings")
    op.drop_table("bookings")
