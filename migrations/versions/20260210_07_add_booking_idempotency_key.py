"""add booking idempotency key

Revision ID: 20260210_07
Revises: 20260209_06
Create Date: 2026-02-10 08:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260210_07"
down_revision: Union[str, None] = "20260209_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "uq_bookings_client_idempotency_key",
        "bookings",
        ["client_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_bookings_client_idempotency_key", "bookings", type_="unique")
    op.drop_column("bookings", "idempotency_key")
