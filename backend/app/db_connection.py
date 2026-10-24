from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


Base = declarative_base()


class DatabaseConfigurationError(RuntimeError):
    """Raised when database access is requested without a configured URL."""


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create an engine without opening a database connection."""
    configured_url = settings.DATABASE_URL if database_url is None else database_url
    if not configured_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured. Set DATABASE_URL to a PostgreSQL "
            "connection URL before requesting database access."
        )

    return create_engine(configured_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions bound to the supplied SQLAlchemy engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@lru_cache(maxsize=1)
def _configured_session_factory() -> sessionmaker[Session]:
    engine = create_database_engine()
    return create_session_factory(engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a session and always closes it."""
    session = _configured_session_factory()()
    try:
        yield session
    finally:
        session.close()
