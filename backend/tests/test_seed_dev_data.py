"""Unit tests for PostgreSQL development seed script (backend/scripts/seed_dev_data.py).

All tests run against an isolated SQLite in-memory database to ensure no writes
touch the live or development database.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db_connection import Base
from app.models import User, Product, Stock, CRMTag
from scripts.seed_dev_data import seed_database, SeedConflictError


@pytest.fixture
def in_memory_session():
    """Fixture supplying a clean SQLite in-memory session with all tables created."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_seed_database_initial_full_seeding(in_memory_session):
    """Seed script populates users and CRM tags correctly (mock products removed)."""
    summary = seed_database(in_memory_session)

    assert summary["users_inserted"] == 2
    assert summary["products_inserted"] == 0
    assert summary["stocks_inserted"] == 0
    assert summary["crm_tags_inserted"] == 1

    users = in_memory_session.query(User).all()
    assert len(users) == 2
    seller = in_memory_session.get(User, "11111111-1111-1111-1111-111111111111")
    assert seller is not None
    assert seller.role == "seller"
    assert seller.email == "seller@fashion.com"

    buyer = in_memory_session.get(User, "22222222-2222-2222-2222-222222222222")
    assert buyer is not None
    assert buyer.role == "buyer"
    assert buyer.email == "buyer@fashion.com"

    products = in_memory_session.query(Product).all()
    assert len(products) == 0

    stocks = in_memory_session.query(Stock).all()
    assert len(stocks) == 0


def test_foreign_keys_validity(in_memory_session, monkeypatch):
    """Verify Foreign Key relationships between User ↔ Product ↔ Stock when products are configured."""
    from app.database import db

    test_product = {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Test Product",
        "description": "Test description",
        "price": 50.00,
        "stock_quantity": 25,
        "category": "Test",
        "seller_id": "11111111-1111-1111-1111-111111111111",
        "is_active": True,
    }
    test_stocks = [
        {
            "id": "55555555-5555-5555-5555-555555555555",
            "product_id": "33333333-3333-3333-3333-333333333333",
            "variant_key": "S",
            "available_quantity": 10,
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": "66666666-6666-6666-6666-666666666666",
            "product_id": "33333333-3333-3333-3333-333333333333",
            "variant_key": "M",
            "available_quantity": 15,
            "updated_at": datetime.now(timezone.utc),
        },
    ]
    monkeypatch.setattr(db, "products", [test_product])
    monkeypatch.setattr(db, "stocks", test_stocks)

    seed_database(in_memory_session)

    product1 = in_memory_session.get(Product, "33333333-3333-3333-3333-333333333333")
    assert product1 is not None
    assert product1.seller_id == "11111111-1111-1111-1111-111111111111"
    assert product1.seller.email == "seller@fashion.com"

    variants = product1.stocks
    assert len(variants) == 2
    variant_keys = {v.variant_key for v in variants}
    assert variant_keys == {"S", "M"}


def test_aggregate_stock_matches_variants(in_memory_session):
    """Product.stock_quantity must equal the sum of Stock.available_quantity of its variants."""
    seed_database(in_memory_session)

    products = in_memory_session.query(Product).all()
    for product in products:
        variant_sum = sum(stock.available_quantity for stock in product.stocks)
        assert product.stock_quantity == variant_sum, (
            f"Product {product.id} stock_quantity ({product.stock_quantity}) "
            f"does not match sum of variants ({variant_sum})"
        )


def test_idempotency_second_run_skips(in_memory_session):
    """Running seed_database twice consecutively must skip all records without duplicating rows."""
    first_summary = seed_database(in_memory_session)
    assert first_summary["users_inserted"] == 2
    assert first_summary["products_inserted"] == 0

    second_summary = seed_database(in_memory_session)
    assert second_summary["users_inserted"] == 0
    assert second_summary["users_skipped"] == 2
    assert second_summary["products_inserted"] == 0
    assert second_summary["products_skipped"] == 0
    assert second_summary["stocks_inserted"] == 0
    assert second_summary["stocks_skipped"] == 0

    assert in_memory_session.query(User).count() == 2
    assert in_memory_session.query(Product).count() == 0
    assert in_memory_session.query(Stock).count() == 0


def test_conflicting_existing_data_raises_error_and_terminates(in_memory_session):
    """If a record with an existing ID has conflicting data, SeedConflictError is raised."""
    now = datetime.now(timezone.utc)
    # Pre-insert a user with conflicting email for the seller ID
    conflicting_user = User(
        id="11111111-1111-1111-1111-111111111111",
        email="imposter@fashion.com",  # Conflict!
        password_hash="$2b$12$somehash",
        role="seller",
        created_at=now,
        updated_at=now,
    )
    in_memory_session.add(conflicting_user)
    in_memory_session.commit()

    with pytest.raises(SeedConflictError, match="Conflict for User ID"):
        seed_database(in_memory_session)

    # Verify original imposter record was not overwritten
    db_user = in_memory_session.get(User, "11111111-1111-1111-1111-111111111111")
    assert db_user.email == "imposter@fashion.com"


def test_transaction_rollback_on_error(in_memory_session, monkeypatch):
    """Transaction must be completely rolled back if an error occurs during seeding."""
    from app.database import db

    # Inject a bad product with mismatching stock quantity into db.products
    bad_product = {
        "id": "99999999-9999-9999-9999-999999999999",
        "name": "Corrupt Item",
        "description": "Corrupt",
        "price": 50.00,
        "stock_quantity": 999,  # Mismatch with variants (0 variants exist)
        "category": "Test",
        "seller_id": "11111111-1111-1111-1111-111111111111",
        "is_active": True,
    }
    
    modified_products = list(db.products) + [bad_product]
    monkeypatch.setattr(db, "products", modified_products)

    with pytest.raises(ValueError, match="does not match sum of variant stocks"):
        seed_database(in_memory_session)

    # Verify that users inserted before the error were rolled back
    users = in_memory_session.query(User).all()
    assert len(users) == 0
