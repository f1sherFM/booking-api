"""create wait list entries

Revision ID: 20260210_08
Revises: 20260210_07
Create Date: 2026-02-10 13:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260210_08"
down_revision: str | None = "20260210_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wait_list_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["slot_id"], ["time_slots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot_id", "client_id", name="uq_wait_list_slot_client"),
    )
    op.create_index(op.f("ix_wait_list_entries_id"), "wait_list_entries", ["id"], unique=False)
    op.create_index(op.f("ix_wait_list_entries_slot_id"), "wait_list_entries", ["slot_id"], unique=False)
    op.create_index(op.f("ix_wait_list_entries_client_id"), "wait_list_entries", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wait_list_entries_client_id"), table_name="wait_list_entries")
    op.drop_index(op.f("ix_wait_list_entries_slot_id"), table_name="wait_list_entries")
    op.drop_index(op.f("ix_wait_list_entries_id"), table_name="wait_list_entries")
    op.drop_table("wait_list_entries")
