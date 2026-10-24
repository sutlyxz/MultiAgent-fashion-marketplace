"""Static / import-only tests for the Alembic migration environment.

These tests verify that:
1. The shared ``Base.metadata`` contains all 12 expected tables.
2. ``env.py`` sets ``target_metadata`` to the shared ``Base.metadata``.
3. A missing ``DATABASE_URL`` raises ``DatabaseConfigurationError``.
4. Importing the FastAPI app does NOT trigger a database connection.
5. No migration or database connection is executed by any test.

Run with:  python -m pytest tests/test_alembic_env.py -v
(from the ``backend/`` directory, or with PYTHONPATH including it)
"""

import importlib
import importlib.util
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Ensure ``backend/`` is on sys.path so ``app.*`` imports resolve.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# 1. Verify all 12 model tables are registered on Base.metadata
# ---------------------------------------------------------------------------

EXPECTED_TABLES = sorted([
    "users",
    "products",
    "stocks",
    "checkout_sessions",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "support_tickets",
    "claims",
    "crm_tags",
    "user_crm_tags",
])


def test_base_metadata_contains_all_tables():
    """Base.metadata must contain exactly the 12 expected ORM tables."""
    from app.db_connection import Base
    import app.models  # noqa: F401 — ensure tables are registered

    registered = sorted(Base.metadata.tables.keys())
    assert registered == EXPECTED_TABLES, (
        f"Expected {EXPECTED_TABLES}, got {registered}"
    )


def test_table_count_is_twelve():
    """Sanity check — there must be exactly 12 tables."""
    from app.db_connection import Base
    import app.models  # noqa: F401

    assert len(Base.metadata.tables) == 12


# ---------------------------------------------------------------------------
# 2. env.py target_metadata points to the shared Base.metadata
# ---------------------------------------------------------------------------

def _load_env_module():
    """Import ``migrations/env.py`` outside the Alembic CLI.

    Outside of Alembic, ``context.is_offline_mode()`` raises a
    ``NameError`` because the proxy is not established.  The module-level
    assignments (including ``target_metadata``) execute before that
    bottom-of-file guard, so we catch the error and return the module
    with its attributes intact.
    """
    migrations_dir = os.path.join(BACKEND_DIR, "migrations")
    env_path = os.path.join(migrations_dir, "env.py")

    # Use a unique name to avoid clashing with cached modules.
    spec = importlib.util.spec_from_file_location(
        "_alembic_env_under_test", env_path,
    )
    assert spec is not None and spec.loader is not None
    env_module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(env_module)
    except (NameError, RuntimeError):
        # Expected: the Alembic context proxy isn't initialised outside
        # the CLI, so is_offline_mode() raises.
        pass
    return env_module


def test_env_target_metadata_is_base_metadata():
    """migrations/env.py must set target_metadata = Base.metadata."""
    from app.db_connection import Base
    import app.models  # noqa: F401

    env_module = _load_env_module()

    assert hasattr(env_module, "target_metadata"), (
        "env.py must define target_metadata at module level"
    )
    assert env_module.target_metadata is Base.metadata, (
        "target_metadata must be the same object as Base.metadata"
    )


def test_env_imports_base_and_models():
    """env.py must import Base and app.models."""
    env_module = _load_env_module()

    # Base should be accessible in the module namespace.
    assert hasattr(env_module, "Base"), "env.py must import Base"
    # The 'app' attribute proves app.models was imported.
    assert "app.models" in sys.modules, (
        "env.py must import app.models to register all tables"
    )


# ---------------------------------------------------------------------------
# 3. Missing DATABASE_URL raises DatabaseConfigurationError
# ---------------------------------------------------------------------------

def test_missing_database_url_raises():
    """When DATABASE_URL is empty, _get_database_url must raise."""
    from app.db_connection import DatabaseConfigurationError
    from unittest.mock import patch

    env_module = _load_env_module()

    assert hasattr(env_module, "_get_database_url"), (
        "env.py must define _get_database_url"
    )

    # Patch the settings reference inside the env module's namespace.
    with patch.object(env_module, "settings") as mock_settings:
        mock_settings.DATABASE_URL = ""
        with pytest.raises(DatabaseConfigurationError):
            env_module._get_database_url()


def test_valid_database_url_returned():
    """When DATABASE_URL is set, _get_database_url returns it."""
    from unittest.mock import patch

    env_module = _load_env_module()
    sentinel_url = "postgresql://user:pass@host/db"

    with patch.object(env_module, "settings") as mock_settings:
        mock_settings.DATABASE_URL = sentinel_url
        assert env_module._get_database_url() == sentinel_url


# ---------------------------------------------------------------------------
# 4. Importing the FastAPI app does not open a DB connection
# ---------------------------------------------------------------------------

def test_fastapi_import_does_not_connect(monkeypatch):
    """Importing app.main must NOT call create_engine or open a connection."""
    call_log = []

    from sqlalchemy import create_engine as _orig

    def spy_create_engine(*args, **kwargs):
        call_log.append(("create_engine", args, kwargs))
        return _orig(*args, **kwargs)

    monkeypatch.setattr("sqlalchemy.create_engine", spy_create_engine)

    # Force re-import so our spy is active.
    if "app.main" in sys.modules:
        importlib.reload(sys.modules["app.main"])
    else:
        import app.main  # noqa: F401

    assert len(call_log) == 0, (
        "create_engine was called during import of app.main — "
        "the application must not open a DB connection at import time."
    )
