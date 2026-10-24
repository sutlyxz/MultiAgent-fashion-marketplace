"""Alembic migration environment for the Fashion Marketplace backend.

This module:
- Imports the shared ``Base`` from ``app.db_connection`` so that
  ``target_metadata`` reflects the exact same table registry used by the
  application's ORM models.
- Imports ``app.models`` to ensure every model class is loaded and its
  table is registered in ``Base.metadata`` before Alembic inspects it.
- Reads the database URL from the project's ``Settings`` (backed by the
  ``DATABASE_URL`` environment variable) — credentials are never logged.
- Fails with a clear ``DatabaseConfigurationError`` when no URL is
  available, instead of silently connecting to a wrong target.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---- Application imports ------------------------------------------------- #
# Import Base FIRST, then models so every table is registered.
from app.db_connection import Base, DatabaseConfigurationError
from app.config import settings

import app.models  # noqa: F401 — registers all tables on Base.metadata

# ---- Alembic setup ------------------------------------------------------- #

# The single source of truth for autogenerate / diff operations.
target_metadata = Base.metadata


# -------------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------------- #

def _get_database_url() -> str:
    """Return the database URL from the application configuration.

    Raises ``DatabaseConfigurationError`` with a developer-friendly
    message when the variable is unset or empty.  The URL value itself
    is never printed or logged to avoid credential leakage.
    """
    url: str = settings.DATABASE_URL
    if not url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured.  Set the DATABASE_URL "
            "environment variable to a PostgreSQL connection URL before "
            "running Alembic migrations."
        )
    return url


# -------------------------------------------------------------------------- #
# Offline (SQL-script) migrations
# -------------------------------------------------------------------------- #

def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to the database.

    Calls ``context.configure`` with just a URL so that
    ``context.execute()`` emits literal SQL instead of executing it.
    """
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------------------------------- #
# Online (live-connection) migrations
# -------------------------------------------------------------------------- #

def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    # Inject the URL into Alembic's config object so that
    # ``engine_from_config`` picks it up without hard-coding.
    alembic_cfg = context.config
    configuration = alembic_cfg.get_section(alembic_cfg.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------------------------------- #
# Entry point — Alembic calls whichever mode is appropriate.
# -------------------------------------------------------------------------- #

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
