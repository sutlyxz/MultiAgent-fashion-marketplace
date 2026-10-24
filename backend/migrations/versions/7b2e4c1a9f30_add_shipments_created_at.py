"""add shipments.created_at

Revision ID: 7b2e4c1a9f30
Revises: d6931d9c9757
Create Date: 2026-10-10 10:15:00.000000+00:00

Adds a timezone-aware ``created_at`` column to ``shipments`` so the latest
shipment for an order can be selected deterministically by
``(created_at, id)``.

Existing rows are handled safely (the table is NOT assumed to be empty):
1. The column is added as nullable.
2. Existing rows are backfilled with ``CURRENT_TIMESTAMP`` (the migration
   time). Their true creation time was never recorded, so this is a
   documented approximation; ``id`` remains the tie-breaker among them.
3. The column is then made ``NOT NULL``.

No server default is left on the column: new rows get their value from the
ORM-side UTC default in ``app.models.Shipment``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b2e4c1a9f30'
down_revision: Union[str, None] = 'd6931d9c9757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'shipments',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE shipments SET created_at = CURRENT_TIMESTAMP "
        "WHERE created_at IS NULL"
    )
    op.alter_column(
        'shipments',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column('shipments', 'created_at')
