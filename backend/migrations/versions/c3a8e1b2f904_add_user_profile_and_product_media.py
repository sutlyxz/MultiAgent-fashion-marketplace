"""add user profile and product media

Revision ID: c3a8e1b2f904
Revises: 7b2e4c1a9f30
Create Date: 2026-10-11 14:35:00.000000+00:00

DRAFT MIGRATION (NOT YET APPLIED TO LIVE POSTGRESQL):
Adds user display name (`name`) and seller store name (`store_name`) to `users`.
Adds product image URL (`image_url`) and primary garment color (`color`) to `products`.

Safety design:
1. Columns added as nullable=True so existing rows remain 100% unaffected.
2. Existing rows retain NULL values until developers/users provide confirmed profile and media data.
3. No speculative backfills or unverified URLs are hardcoded into migration logic.
4. Downgrade explicitly drops the added columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a8e1b2f904'
down_revision: Union[str, None] = '7b2e4c1a9f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add profile fields to users (nullable=True for safety)
    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('store_name', sa.String(length=255), nullable=True))

    # 2. Add media & garment color fields to products (nullable=True for safety)
    op.add_column('products', sa.Column('image_url', sa.String(length=1024), nullable=True))
    op.add_column('products', sa.Column('color', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # WARNING: Dropping these columns will discard any user-provided name, store_name, image_url, and color data.
    op.drop_column('products', 'color')
    op.drop_column('products', 'image_url')
    op.drop_column('users', 'store_name')
    op.drop_column('users', 'name')
