import importlib
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import config
from app import db_connection


@pytest.fixture(autouse=True)
def clear_cached_session_factory():
    db_connection._configured_session_factory.cache_clear()
    yield
    db_connection._configured_session_factory.cache_clear()


def test_connection_module_import_does_not_require_database_configuration(
    monkeypatch,
):
    monkeypatch.setattr(config.settings, "DATABASE_URL", "")

    reloaded_module = importlib.reload(db_connection)

    assert reloaded_module.Base is not None
    assert reloaded_module.create_database_engine
    assert importlib.import_module("app.main").app


def test_missing_database_url_raises_actionable_configuration_error(monkeypatch):
    monkeypatch.setattr(config.settings, "DATABASE_URL", "")

    with pytest.raises(
        db_connection.DatabaseConfigurationError,
        match="Set DATABASE_URL",
    ):
        db_connection.create_database_engine()

    with pytest.raises(
        db_connection.DatabaseConfigurationError,
        match="Set DATABASE_URL",
    ):
        next(db_connection.get_db())


def test_session_factory_creates_bound_session_without_connecting():
    engine = db_connection.create_database_engine("sqlite://")
    session_factory = db_connection.create_session_factory(engine)

    session = session_factory()
    try:
        assert isinstance(engine, Engine)
        assert isinstance(session, Session)
        assert session.get_bind() is engine
    finally:
        session.close()
        engine.dispose()


def test_get_db_closes_session_when_dependency_finishes(monkeypatch):
    engine = db_connection.create_database_engine("sqlite://")
    session_factory = db_connection.create_session_factory(engine)
    monkeypatch.setattr(
        db_connection,
        "_configured_session_factory",
        lambda: session_factory,
    )

    dependency = db_connection.get_db()
    session = next(dependency)
    closed = False
    original_close = session.close

    def record_close():
        nonlocal closed
        closed = True
        original_close()

    monkeypatch.setattr(session, "close", record_close)
    if hasattr(dependency, "close"):
        dependency.close()

    assert closed
    engine.dispose()
