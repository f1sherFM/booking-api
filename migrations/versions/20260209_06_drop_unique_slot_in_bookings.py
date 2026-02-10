"""drop unique slot constraint in bookings

Revision ID: 20260209_06
Revises: 20260209_05
Create Date: 2026-02-09 19:58:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260209_06"
down_revision: Union[str, None] = "20260209_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_bookings_slot_id", "bookings", type_="unique")
    op.create_index("ix_bookings_slot_id", "bookings", ["slot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_slot_id", table_name="bookings")
    op.create_unique_constraint("uq_bookings_slot_id", "bookings", ["slot_id"])
