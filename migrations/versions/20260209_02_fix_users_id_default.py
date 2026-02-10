"""fix users id default sequence

Revision ID: 20260209_02
Revises: 20260209_01
Create Date: 2026-02-09 17:58:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260209_02"
down_revision: Union[str, None] = "20260209_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE col_default text;
        BEGIN
            SELECT column_default
            INTO col_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'users'
              AND column_name = 'id';

            IF col_default IS NULL THEN
                CREATE SEQUENCE IF NOT EXISTS users_id_seq OWNED BY users.id;
                PERFORM setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false);
                ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'id'
                  AND column_default LIKE 'nextval(%'
            ) THEN
                ALTER TABLE users ALTER COLUMN id DROP DEFAULT;
            END IF;
        END $$;
        """
    )
