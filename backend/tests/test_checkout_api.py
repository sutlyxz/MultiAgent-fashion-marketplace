"""Unit tests for Checkout API (fast-link session creation and retrieval) connected to PostgreSQL / SQLAlchemy.

All tests use FastAPI TestClient and an isolated SQLite in-memory database
by overriding the `get_db` dependency. No live or dev database is touched.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token, hash_password
from app.db_connection import Base, get_db
from app.main import app
from app.models import CheckoutSession, Product, Stock, User


@pytest.fixture
def test_db_session():
    """Create an isolated SQLite in-memory database and populate test seed data."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    # 1. Seed Users (User A & User B)
    user_a = User(
        id="usr-chk-100",
        email="buyer_chk_a@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    user_b = User(
        id="usr-chk-200",
        email="buyer_chk_b@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    seller = User(
        id="usr-chk-seller",
        email="seller_chk@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add_all([user_a, user_b, seller])
    session.flush()

    # 2. Seed Product
    product = Product(
        id="prod-chk-100",
        name="Checkout Test Shirt",
        description="Shirt for checkout tests",
        price=Decimal("29.99"),
        stock_quantity=10,
        category="Shirts",
        seller_id="usr-chk-seller",
        is_active=True,
    )
    session.add(product)
    session.flush()

    # 3. Seed Stock Variant
    stock = Stock(
        id="stk-chk-101",
        product_id="prod-chk-100",
        variant_key="M",
        available_quantity=10,
        updated_at=now,
    )
    session.add(stock)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(test_db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_a_token():
    return create_access_token({"sub": "buyer_chk_a@fashion.com"})


@pytest.fixture
def user_b_token():
    return create_access_token({"sub": "buyer_chk_b@fashion.com"})


def test_create_fast_link_success(client, user_a_token, test_db_session):
    """1. Create Fast Link session successfully and verify DB storage."""
    payload = {
        "product_id": "prod-chk-100",
        "variant_key": "M",
        "quantity": 2,
    }
    headers = {"Authorization": f"Bearer {user_a_token}"}
    res = client.post("/api/checkout/fast-link", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "token" in data
    token = data["token"]
    assert token.startswith("FL-")
    assert "expires_at" in data
    assert data["checkout_url"] == f"/checkout/fast-link/{token}"

    # Verify session is saved in DB under token SHA-256 hash
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db_session = test_db_session.scalar(
        select(CheckoutSession).where(CheckoutSession.token_hash == token_hash)
    )
    assert db_session is not None
    assert db_session.user_id == "usr-chk-100"
    assert db_session.product_id == "prod-chk-100"
    assert db_session.stock_id == "stk-chk-101"
    assert db_session.variant_key == "M"
    assert db_session.quantity == 2
    assert db_session.status == "OPEN"


def test_create_fast_link_invalid_variant(client, user_a_token):
    """3. Reject non-existent Product or Stock Variant with 404."""
    payload = {
        "product_id": "prod-chk-100",
        "variant_key": "XXL",
        "quantity": 1,
    }
    headers = {"Authorization": f"Bearer {user_a_token}"}
    res = client.post("/api/checkout/fast-link", json=payload, headers=headers)
    assert res.status_code == 404
    assert res.json() == {"detail": "Product variant not found"}


def test_create_fast_link_invalid_quantity(client, user_a_token):
    """4. Reject quantity <= 0 with 400."""
    payload = {
        "product_id": "prod-chk-100",
        "variant_key": "M",
        "quantity": 0,
    }
    headers = {"Authorization": f"Bearer {user_a_token}"}
    res = client.post("/api/checkout/fast-link", json=payload, headers=headers)
    assert res.status_code == 400
    assert res.json() == {"detail": "Quantity must be greater than zero"}


def test_get_fast_link_session_success(client, user_a_token):
    """5. Retrieve fast link session with valid token."""
    # Create fast link first
    create_res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 3},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    token = create_res.json()["token"]

    # Retrieve fast link session
    get_res = client.get(
        f"/api/checkout/fast-link/{token}",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert get_res.status_code == 200
    data = get_res.json()

    assert data["user_id"] == "usr-chk-100"
    assert data["product_id"] == "prod-chk-100"
    assert data["stock_id"] == "stk-chk-101"
    assert data["variant_key"] == "M"
    assert data["quantity"] == 3
    assert data["status"] == "OPEN"
    assert data["is_fulfillable"] is True
    assert data["available_quantity"] == 10


def test_get_fast_link_session_invalid_token(client, user_a_token):
    """6. Invalid token or missing session returns 404."""
    res = client.get(
        "/api/checkout/fast-link/FL-invalidtoken999",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert res.status_code == 404
    assert res.json() == {"detail": "Checkout session not found"}


def test_get_fast_link_session_expired(client, user_a_token, test_db_session):
    """7. Expired session returns 400 error and marks status EXPIRED."""
    create_res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 1},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    token = create_res.json()["token"]
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Manually expire the session in test DB
    sess = test_db_session.scalar(
        select(CheckoutSession).where(CheckoutSession.token_hash == token_hash)
    )
    sess.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    test_db_session.commit()

    # Try retrieving expired session
    res = client.get(
        f"/api/checkout/fast-link/{token}",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert res.status_code == 400
    assert res.json() == {"detail": "Checkout session has expired"}


def test_get_fast_link_session_unauthorized_user(client, user_a_token, user_b_token):
    """8. Session accessed by another user returns 403."""
    create_res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 1},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    token = create_res.json()["token"]

    # User B tries to access User A's session
    res = client.get(
        f"/api/checkout/fast-link/{token}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert res.status_code == 403
    assert res.json() == {"detail": "You do not have access to this checkout session"}


def test_token_is_hashed_in_database(client, user_a_token, test_db_session):
    """9. Plaintext token is not stored directly in token_hash column."""
    create_res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 1},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    token = create_res.json()["token"]

    # Check database rows
    all_sessions = test_db_session.query(CheckoutSession).all()
    stored_hashes = [s.token_hash for s in all_sessions]

    assert token not in stored_hashes, "Plaintext token must NOT be stored in DB"
    assert hashlib.sha256(token.encode("utf-8")).hexdigest() in stored_hashes


def test_stock_not_decremented_by_checkout(client, user_a_token, test_db_session):
    """10. Creating checkout session does not modify stock levels."""
    client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 5},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )

    stk = test_db_session.get(Stock, "stk-chk-101")
    assert stk.available_quantity == 10


def test_checkout_does_not_depend_on_in_memory_db(client, user_a_token, monkeypatch):
    """11. Checkout operates on DB even if in-memory db.checkout_sessions is cleared."""
    from app.database import db

    monkeypatch.setattr(db, "checkout_sessions", [])
    monkeypatch.setattr(db, "stocks", [])

    create_res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 1},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert create_res.status_code == 200
    token = create_res.json()["token"]

    get_res = client.get(
        f"/api/checkout/fast-link/{token}",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["quantity"] == 1


# ---------------------------------------------------------------------------
# FR-02: Fast-link checkout cannot be used by seller to buy own product
# ---------------------------------------------------------------------------

def test_seller_cannot_create_fast_link_for_own_product(client, test_db_session):
    """Sellers cannot create a fast-link checkout session for their own products."""
    from app.auth import create_access_token

    # seller-chk owns prod-chk-100
    seller_token = create_access_token({"sub": "seller_chk@fashion.com"})

    res = client.post(
        "/api/checkout/fast-link",
        json={"product_id": "prod-chk-100", "variant_key": "M", "quantity": 1},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert res.status_code == 400
    assert "Sellers cannot purchase their own products" in res.json()["detail"]

