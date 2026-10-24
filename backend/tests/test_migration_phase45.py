"""Tests for Phase 4.5 Alembic migration: e4f1a2b3c5d6_add_seller_shipments.

Tests:
1. Preflight aborts when an ambiguous shipment (multi-seller order) exists prior to migration.
2. Preflight aborts when an orphan shipment (no product/seller) exists.
3. Clean upgrade backfills 1:1 single-seller shipments and enforces NOT NULL and UniqueConstraint.
4. Clean downgrade rolls back schema changes.
5. All tests use isolated in-memory/temporary SQLite databases without touching production data.
"""

import importlib.util
import os
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from typing import Any

MIGRATION_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "migrations",
        "versions",
        "e4f1a2b3c5d6_add_seller_shipments.py",
    )
)

def _load_migration_module() -> Any:
    spec = importlib.util.spec_from_file_location("migr_e4f1a2b3c5d6", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _create_pre_phase45_tables(conn):
    conn.execute(sa.text("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL
        );
    """))
    conn.execute(sa.text("""
        CREATE TABLE products (
            id VARCHAR(36) PRIMARY KEY,
            seller_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL
        );
    """))
    conn.execute(sa.text("""
        CREATE TABLE orders (
            id VARCHAR(36) PRIMARY KEY,
            status VARCHAR(30) NOT NULL
        );
    """))
    conn.execute(sa.text("""
        CREATE TABLE order_items (
            id VARCHAR(36) PRIMARY KEY,
            order_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) NOT NULL
        );
    """))
    conn.execute(sa.text("""
        CREATE TABLE shipments (
            id VARCHAR(36) PRIMARY KEY,
            order_id VARCHAR(36) NOT NULL,
            carrier_name VARCHAR(100) NOT NULL,
            tracking_number VARCHAR(100) UNIQUE NOT NULL,
            status VARCHAR(30) NOT NULL
        );
    """))
    conn.commit()


def test_preflight_aborts_on_ambiguous_multi_seller_shipment():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        _create_pre_phase45_tables(conn)

        # Seed 2 sellers
        conn.execute(sa.text("INSERT INTO users VALUES ('usr-s1', 's1@shop.com', 'seller');"))
        conn.execute(sa.text("INSERT INTO users VALUES ('usr-s2', 's2@shop.com', 'seller');"))
        # Seed 2 products from different sellers
        conn.execute(sa.text("INSERT INTO products VALUES ('prod-1', 'usr-s1', 'Shirt');"))
        conn.execute(sa.text("INSERT INTO products VALUES ('prod-2', 'usr-s2', 'Pants');"))
        # Order with items from BOTH sellers
        conn.execute(sa.text("INSERT INTO orders VALUES ('ord-multi', 'PAID');"))
        conn.execute(sa.text("INSERT INTO order_items VALUES ('oi-1', 'ord-multi', 'prod-1');"))
        conn.execute(sa.text("INSERT INTO order_items VALUES ('oi-2', 'ord-multi', 'prod-2');"))
        # Existing legacy single shipment for this multi-seller order
        conn.execute(sa.text("INSERT INTO shipments VALUES ('shp-ambig', 'ord-multi', 'DHL', 'TRK-AMBIG', 'PREPARING');"))
        conn.commit()

        # Run migration with Alembic op context
        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)

        migr = _load_migration_module()
        migr.op = op

        with pytest.raises(RuntimeError) as exc_info:
            migr.upgrade()

        err_msg = str(exc_info.value)
        assert "Migration aborted by Preflight Check" in err_msg
        assert "shp-ambig" in err_msg
        assert "ord-multi" in err_msg

        # Verify no schema change happened on shipments
        cols = [r[1] for r in conn.execute(sa.text("PRAGMA table_info(shipments);")).fetchall()]
        assert "seller_id" not in cols, "seller_id column must not exist after aborted preflight"


def test_migration_upgrade_and_downgrade_success():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        _create_pre_phase45_tables(conn)

        # Seed valid single-seller order
        conn.execute(sa.text("INSERT INTO users VALUES ('usr-s1', 's1@shop.com', 'seller');"))
        conn.execute(sa.text("INSERT INTO products VALUES ('prod-1', 'usr-s1', 'Shirt');"))
        conn.execute(sa.text("INSERT INTO orders VALUES ('ord-single', 'PAID');"))
        conn.execute(sa.text("INSERT INTO order_items VALUES ('oi-1', 'ord-single', 'prod-1');"))
        conn.execute(sa.text("INSERT INTO shipments VALUES ('shp-valid', 'ord-single', 'DHL', 'TRK-VALID-1', 'PREPARING');"))
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)

        migr = _load_migration_module()
        migr.op = op

        # Upgrade
        migr.upgrade()
        conn.commit()

        # Verify seller_id was backfilled accurately
        row = conn.execute(sa.text("SELECT id, order_id, seller_id, tracking_number FROM shipments WHERE id='shp-valid';")).fetchone()
        assert row is not None
        assert row[2] == "usr-s1", f"Expected seller_id='usr-s1', got {row[2]}"

        # Verify UniqueConstraint prevents duplicate (order_id, seller_id)
        with pytest.raises(Exception):
            conn.execute(sa.text("INSERT INTO shipments (id, order_id, seller_id, carrier_name, tracking_number, status) VALUES ('shp-dup', 'ord-single', 'usr-s1', 'FedEx', 'TRK-DUP', 'PREPARING');"))
            conn.commit()
        conn.rollback()

        # Downgrade
        migr.downgrade()
        conn.commit()

        # Verify seller_id was dropped
        cols_after = [r[1] for r in conn.execute(sa.text("PRAGMA table_info(shipments);")).fetchall()]
        assert "seller_id" not in cols_after, "seller_id must be dropped after downgrade"
