"""add case-insensitive unique index for store_name

Revision ID: f5a2b3c4d5e6
Revises: e4f1a2b3c5d6
Create Date: 2026-10-15 12:00:00.000000+00:00

Single Account — Buyer + Seller:
1. Preflight check: Validates no case-insensitive duplicate store names exist
   in the database before applying the unique index.
   Aborts without making any DDL changes if conflicts are found so human
   review can decide without data loss.
2. Index creation: Adds unique index uq_users_store_name_lower on LOWER(store_name)
   where store_name IS NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a2b3c4d5e6'
down_revision: Union[str, None] = 'e4f1a2b3c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Preflight Check: verify zero case-insensitive duplicate store names
    preflight_sql = sa.text("""
        SELECT LOWER(TRIM(store_name)) AS lower_name, COUNT(*) AS count_dupes
        FROM users
        WHERE store_name IS NOT NULL AND TRIM(store_name) != ''
        GROUP BY LOWER(TRIM(store_name))
        HAVING COUNT(*) > 1
    """)
    duplicates = conn.execute(preflight_sql).fetchall()
    if duplicates:
        details = ", ".join(f"(name='{r[0]}', count={r[1]})" for r in duplicates)
        raise RuntimeError(
            f"Migration aborted by Preflight Check: Conflicting duplicate store names found: {details}. "
            f"Cannot safely create unique index without human intervention. Migration stopped."
        )

    # 2. Create case-insensitive unique index on users(LOWER(store_name)) where store_name IS NOT NULL
    op.create_index(
        'uq_users_store_name_lower',
        'users',
        [sa.text('LOWER(store_name)')],
        unique=True,
        postgresql_where=sa.text('store_name IS NOT NULL'),
        sqlite_where=sa.text('store_name IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_users_store_name_lower', table_name='users')
