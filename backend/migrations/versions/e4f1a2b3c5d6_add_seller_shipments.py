"""add seller shipments and multi-seller constraints

Revision ID: e4f1a2b3c5d6
Revises: c3a8e1b2f904
Create Date: 2026-10-14 16:00:00.000000+00:00

Phase 4.5 — Order Fulfillment & Shipment:
1. Preflight check: Validates all existing shipments belong to orders where exactly 1 distinct seller can be identified.
   Aborts without making any DDL changes if ambiguous shipments are found.
2. Schema alteration: Adds seller_id (nullable) and alters tracking_number to nullable=True.
3. Backfill: Populates seller_id using exact 1-to-1 matching from order_items and products.
4. Post-backfill validation: Ensures zero NULL seller_id rows remain.
5. Constraint enforcement: Sets seller_id NOT NULL, creates FK to users.id, and creates unique constraint on (order_id, seller_id).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f1a2b3c5d6'
down_revision: Union[str, None] = 'c3a8e1b2f904'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Preflight Check
    preflight_sql = sa.text("""
        SELECT s.id AS shipment_id, s.order_id, COUNT(DISTINCT p.seller_id) AS distinct_sellers
        FROM shipments s
        LEFT JOIN order_items oi ON s.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.id
        GROUP BY s.id, s.order_id
        HAVING COUNT(DISTINCT p.seller_id) != 1
    """)
    ambiguous = conn.execute(preflight_sql).fetchall()
    if ambiguous:
        details = ", ".join(f"(shipment_id={r[0]}, order_id={r[1]}, sellers={r[2]})" for r in ambiguous)
        raise RuntimeError(
            f"Migration aborted by Preflight Check: Found {len(ambiguous)} shipments with ambiguous or missing sellers: {details}. "
            f"Cannot safely backfill without guessing. Please resolve these shipments manually."
        )

    # 2. Add nullable seller_id and allow nullable tracking_number
    with op.batch_alter_table('shipments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('seller_id', sa.String(length=36), nullable=True))
        batch_op.alter_column('tracking_number', existing_type=sa.String(length=100), nullable=True)

    # 3. Backfill seller_id for existing single-seller orders
    backfill_sql = sa.text("""
        UPDATE shipments AS s
        SET seller_id = (
            SELECT MIN(p.seller_id)
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = s.order_id
            GROUP BY oi.order_id
            HAVING COUNT(DISTINCT p.seller_id) = 1
        )
        WHERE s.seller_id IS NULL
    """)
    conn.execute(backfill_sql)

    # 4. Post-Backfill Validation
    null_count = conn.execute(sa.text("SELECT COUNT(*) FROM shipments WHERE seller_id IS NULL")).scalar()
    if null_count is None:
        raise RuntimeError(
            "Migration failed post-backfill validation: unable to determine count of shipments with NULL seller_id."
        )
    if null_count > 0:
        raise RuntimeError(
            f"Migration failed post-backfill validation: {null_count} shipments still have NULL seller_id. "
            f"Aborting constraint enforcement."
        )

    # 5. Enforce NOT NULL, Foreign Key, and Unique Constraint
    with op.batch_alter_table('shipments', schema=None) as batch_op:
        batch_op.alter_column('seller_id', existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key('fk_shipments_seller_id', 'users', ['seller_id'], ['id'], ondelete='RESTRICT')
        batch_op.create_unique_constraint('uq_shipments_order_seller', ['order_id', 'seller_id'])


def downgrade() -> None:
    with op.batch_alter_table('shipments', schema=None) as batch_op:
        batch_op.drop_constraint('uq_shipments_order_seller', type_='unique')
        batch_op.drop_constraint('fk_shipments_seller_id', type_='foreignkey')
        batch_op.alter_column('tracking_number', existing_type=sa.String(length=100), nullable=False)
        batch_op.drop_column('seller_id')
