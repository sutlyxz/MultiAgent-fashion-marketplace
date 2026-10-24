"""Tests for Single Account Alembic migration: f5a2b3c4d5e6_add_case_insensitive_unique_store_name.

Validates:
1. Preflight aborts when case-insensitive duplicate store names exist prior to migration.
2. Clean upgrade creates unique index on LOWER(store_name) where store_name IS NOT NULL.
3. Clean downgrade drops the unique index.
4. Isolated in-memory SQLite database without touching production data.
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
        "f5a2b3c4d5e6_add_case_insensitive_unique_store_name.py",
    )
)


def _load_migration_module() -> Any:
    spec = importlib.util.spec_from_file_location("migr_f5a2b3c4d5e6", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _create_users_table(conn):
    conn.execute(sa.text("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(255),
            store_name VARCHAR(255),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
    """))


def test_preflight_aborts_when_duplicate_store_names_exist(monkeypatch):
    """Preflight check must raise RuntimeError without applying DDL when conflicting names exist."""
    mod = _load_migration_module()
    engine = sa.create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        _create_users_table(conn)
        # Seed case-insensitive duplicate store names
        conn.execute(sa.text("""
            INSERT INTO users (id, email, role, store_name)
            VALUES 
                ('u1', 'seller1@fashion.com', 'seller', 'Vintage Bloom'),
                ('u2', 'seller2@fashion.com', 'seller', 'vintage bloom');
        """))
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        monkeypatch.setattr(mod.op, "get_bind", lambda: conn)
        monkeypatch.setattr(mod.op, "create_index", op.create_index)

        with pytest.raises(RuntimeError) as exc_info:
            mod.upgrade()

        assert "Migration aborted by Preflight Check" in str(exc_info.value)
        assert "vintage bloom" in str(exc_info.value).lower()


def test_upgrade_and_downgrade_clean_execution(monkeypatch):
    """Clean upgrade enforces unique constraint, and downgrade drops it."""
    mod = _load_migration_module()
    engine = sa.create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        _create_users_table(conn)
        # Seed valid non-duplicate users (including multiple buyers with NULL store_name)
        conn.execute(sa.text("""
            INSERT INTO users (id, email, role, store_name)
            VALUES 
                ('u1', 'seller1@fashion.com', 'seller', 'Alpha Atelier'),
                ('u2', 'buyer1@fashion.com', 'buyer', NULL),
                ('u3', 'buyer2@fashion.com', 'buyer', NULL);
        """))
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        monkeypatch.setattr(mod.op, "get_bind", lambda: conn)
        monkeypatch.setattr(mod.op, "create_index", op.create_index)
        monkeypatch.setattr(mod.op, "drop_index", op.drop_index)

        # 1. Upgrade succeeds
        mod.upgrade()
        conn.commit()

        # 2. Case-insensitive duplicate insert fails with IntegrityError
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(sa.text("""
                INSERT INTO users (id, email, role, store_name)
                VALUES ('u4', 'seller4@fashion.com', 'seller', 'alpha atelier');
            """))
            conn.commit()
        conn.rollback()

        # 3. Multiple NULL store_names remain allowed
        conn.execute(sa.text("""
            INSERT INTO users (id, email, role, store_name)
            VALUES ('u5', 'buyer3@fashion.com', 'buyer', NULL);
        """))
        conn.commit()

        # 4. Downgrade drops index
        mod.downgrade()
        conn.commit()

        # After downgrade, duplicate name is allowed
        conn.execute(sa.text("""
            INSERT INTO users (id, email, role, store_name)
            VALUES ('u6', 'seller6@fashion.com', 'seller', 'alpha atelier');
        """))
        conn.commit()
