
"""PostgreSQL Test Harness & Safety Validator for Fashion Marketplace.

Integration and concurrency tests must use the isolated PostgreSQL test database.
The development database must never be used as a test database.
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


ALLOWED_TEST_DATABASE_NAME = "fashion_marketplace_test"

TABLES_IN_CLEANUP_ORDER = [
    "claims",
    "user_crm_tags",
    "crm_tags",
    "support_tickets",
    "shipments",
    "payments",
    "order_items",
    "orders",
    "checkout_sessions",
    "stocks",
    "products",
    "users",
]


class DatabaseSafetyError(RuntimeError):
    """Raised when test-database safety validation fails."""


def validate_test_database_url(
    test_url: Optional[str],
    dev_url: Optional[str] = None,
) -> str:
    """Accept only a PostgreSQL URL targeting the test database."""

    if not test_url or not test_url.strip():
        raise DatabaseSafetyError(
            "TEST_DATABASE_URL is not set. "
            "A dedicated PostgreSQL test database is required."
        )

    test_url = test_url.strip()
    parsed_test = urlparse(test_url)

    if (
        not parsed_test.scheme
        or not parsed_test.scheme.startswith("postgresql")
    ):
        raise DatabaseSafetyError(
            "TEST_DATABASE_URL must be a valid PostgreSQL connection URL."
        )

    test_db_name = (parsed_test.path or "").lstrip("/").lower()

    if not test_db_name:
        raise DatabaseSafetyError(
            "TEST_DATABASE_URL does not specify a database name."
        )

    if test_db_name == "fashion_marketplace_dev":
        raise DatabaseSafetyError(
            "SAFETY VIOLATION: The development database 'fashion_marketplace_dev' cannot "
            "be used for testing."
        )

    if dev_url and dev_url.strip():
        dev_url = dev_url.strip()

        if test_url == dev_url:
            raise DatabaseSafetyError(
                "SAFETY VIOLATION: TEST_DATABASE_URL is identical "
                "to DATABASE_URL."
            )

        parsed_dev = urlparse(dev_url)
        dev_db_name = (parsed_dev.path or "").lstrip("/").lower()

        if (
            parsed_test.hostname == parsed_dev.hostname
            and parsed_test.port == parsed_dev.port
            and test_db_name == dev_db_name
        ):
            raise DatabaseSafetyError(
                "SAFETY VIOLATION: Test and development URLs "
                "target the same database."
            )

    # Strict allowlist: no other database name is permitted.
    if test_db_name != ALLOWED_TEST_DATABASE_NAME:
        raise DatabaseSafetyError(
            f"SAFETY VIOLATION: Database name '{test_db_name}' is not in allowlist. "
            f"Only the database '{ALLOWED_TEST_DATABASE_NAME}' is permitted."
        )

    return test_url


def is_postgres_test_db_available() -> bool:
    """Check whether a safe TEST_DATABASE_URL is configured."""

    try:
        validate_test_database_url(
            os.getenv("TEST_DATABASE_URL"),
            os.getenv("DATABASE_URL"),
        )
        return True
    except DatabaseSafetyError:
        return False


def verify_active_database(engine: Engine) -> str:
    """Verify the actual connected PostgreSQL database name."""

    with engine.connect() as conn:
        active_db = conn.scalar(text("SELECT current_database();"))

    if not active_db:
        raise DatabaseSafetyError(
            "Unable to query active database."
        )

    active_db_lower = str(active_db).lower()

    if active_db_lower == "fashion_marketplace_dev":
        raise DatabaseSafetyError(
            "CRITICAL SAFETY VIOLATION: Connected database is 'fashion_marketplace_dev'! "
            "Development database cannot be used for testing."
        )

    if active_db_lower != ALLOWED_TEST_DATABASE_NAME:
        raise DatabaseSafetyError(
            f"CRITICAL SAFETY VIOLATION: Connected database '{active_db_lower}' is not in allowlist. "
            f"Only the approved test database '{ALLOWED_TEST_DATABASE_NAME}' is permitted."
        )

    return active_db_lower


def create_safe_test_engine(test_url: str) -> Engine:
    """Create an engine only after validating its live database."""

    validate_test_database_url(test_url, os.getenv("DATABASE_URL"))

    engine = create_engine(test_url, pool_pre_ping=True)

    try:
        verify_active_database(engine)
    except Exception:
        engine.dispose()
        raise

    return engine


def _resolve_alembic_ini(
    alembic_ini_path: Optional[str],
    backend_dir: Path,
) -> Path:
    """Resolve alembic.ini independently of the current working directory."""

    if not alembic_ini_path:
        config_path = backend_dir / "alembic.ini"
    else:
        supplied_path = Path(alembic_ini_path)

        if supplied_path.is_absolute():
            candidates = [supplied_path]
        else:
            candidates = [
                Path.cwd() / supplied_path,
                backend_dir / supplied_path,
                backend_dir.parent / supplied_path,
            ]

        config_path = next(
            (candidate for candidate in candidates if candidate.is_file()),
            candidates[0],
        )

    config_path = config_path.resolve()

    if not config_path.is_file():
        raise FileNotFoundError(
            "Alembic configuration file was not found. "
            f"Expected an existing alembic.ini; resolved path: {config_path}"
        )

    return config_path


def apply_test_migrations(
    test_url: str,
    alembic_ini_path: Optional[str] = None,
) -> None:
    """Apply migrations to the verified test database only."""

    from app.config import settings

    # Validate the URL before any database operation.
    validate_test_database_url(
        test_url,
        os.getenv("DATABASE_URL"),
    )

    backend_dir = Path(__file__).resolve().parents[1]
    migrations_dir = backend_dir / "migrations"
    alembic_ini = _resolve_alembic_ini(
        alembic_ini_path,
        backend_dir,
    )

    if not migrations_dir.is_dir():
        raise FileNotFoundError(
            f"Alembic migrations directory not found: {migrations_dir}"
        )

    # Verify the live target before Alembic can modify the database.
    verification_engine = create_engine(
        test_url,
        pool_pre_ping=True,
    )

    try:
        verify_active_database(verification_engine)
    finally:
        verification_engine.dispose()

    # Explicitly configure both paths instead of relying on the
    # process's current working directory or the INI defaults.
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option(
        "script_location",
        str(migrations_dir.resolve()),
    )

    # This project's env.py reads settings.DATABASE_URL directly.
    # Override it temporarily, then restore it even if migration fails.
    original_url = settings.DATABASE_URL

    try:
        settings.DATABASE_URL = test_url
        command.upgrade(alembic_cfg, "head")
    finally:
        settings.DATABASE_URL = original_url


def clean_test_database_rows(session: Session) -> None:
    """Delete test rows in FK-safe order without dropping tables."""

    try:
        for table in TABLES_IN_CLEANUP_ORDER:
            session.execute(text(f"DELETE FROM {table};"))

        session.commit()
    except Exception:
        session.rollback()
        raise