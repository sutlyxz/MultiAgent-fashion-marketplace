"""PostgreSQL Integration & Concurrency Test Suite for Fashion Marketplace.

These tests execute against a real PostgreSQL test database to verify:
1. Row-Level Locking (SELECT ... FOR UPDATE)
2. Concurrent Fulfillment prevention on the same order
3. Concurrent Stock Deduction preventing overselling when competing for the last item
4. Payment attempts, slip verification, and idempotent shipment creation
5. Transaction rollback integrity
6. Auth, Checkout, Products, Orders, Claims, and CRM Tags on PostgreSQL

CRITICAL SAFETY REQUIREMENT:
These tests are SKIPPED by default unless TEST_DATABASE_URL is set and strictly
verified to point to an isolated PostgreSQL test database (different from
fashion_marketplace_dev).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import sys
from typing import Any
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

TESTS_DIR = os.path.dirname(__file__)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from app.auth import create_access_token, hash_password
from app.config import settings
from app.db_connection import get_db
from app.main import app
from app.models import (
    Claim,
    CRMTag,
    Order,
    OrderItem,
    Payment,
    Product,
    Shipment,
    Stock,
    SupportTicket,
    User,
    UserCRMTag,
)
from app.routers.orders import verify_payment_and_decrement_stock_db
from postgres_test_harness import (
    ALLOWED_TEST_DATABASE_NAME,
    DatabaseSafetyError,
    apply_test_migrations,
    clean_test_database_rows,
    create_safe_test_engine,
    is_postgres_test_db_available,
    validate_test_database_url,
    verify_active_database,
)

postgres_required = pytest.mark.skipif(
    not is_postgres_test_db_available(),
    reason="PostgreSQL Integration tests require a dedicated, verified TEST_DATABASE_URL.",
)


# =========================================================================== #
# Safety Unit Tests (Always run - no real database connection required)
# =========================================================================== #

def test_safety_validator_rejects_missing_url():
    """1. Rejects immediately if TEST_DATABASE_URL is missing or empty."""
    with pytest.raises(DatabaseSafetyError, match="TEST_DATABASE_URL is not set"):
        validate_test_database_url(None)
    with pytest.raises(DatabaseSafetyError, match="TEST_DATABASE_URL is not set"):
        validate_test_database_url("   ")


def test_safety_validator_rejects_non_postgresql_scheme():
    """2. Rejects if driver scheme is not postgresql."""
    with pytest.raises(DatabaseSafetyError, match="valid PostgreSQL"):
        validate_test_database_url("mysql://user:pass@localhost:3306/fashion_marketplace_test")
    with pytest.raises(DatabaseSafetyError, match="valid PostgreSQL"):
        validate_test_database_url("sqlite:///fashion_marketplace_test.db")


def test_safety_validator_rejects_missing_db_name():
    """3. Rejects if no database name is specified in URL."""
    with pytest.raises(DatabaseSafetyError, match="does not specify a database name"):
        validate_test_database_url("postgresql://user:pass@localhost:5432/")


def test_safety_validator_rejects_dev_database_url():
    """4. Rejects immediately if URL points to fashion_marketplace_dev."""
    with pytest.raises(DatabaseSafetyError, match="fashion_marketplace_dev"):
        validate_test_database_url("postgresql://user:pass@localhost:5432/fashion_marketplace_dev")


def test_safety_validator_rejects_identical_to_dev_url():
    """5. Rejects immediately if URL matches development DATABASE_URL."""
    dev = "postgresql://user:pass@localhost:5432/fashion_marketplace_test"
    with pytest.raises(DatabaseSafetyError, match="identical"):
        validate_test_database_url(dev, dev_url=dev)


def test_safety_validator_rejects_databases_not_in_allowlist():
    """6. Rejects any database name not strictly equal to fashion_marketplace_test."""
    unauthorized_urls = [
        "postgresql://user:pass@localhost:5432/other_test_db",
        "postgresql://user:pass@localhost:5432/fashion_marketplace_staging",
        "postgresql://user:pass@localhost:5432/test_db",
        "postgresql://user:pass@localhost:5432/my_test_db",
        "postgresql://user:pass@localhost:5432/fashion_test",
    ]
    for url in unauthorized_urls:
        with pytest.raises(DatabaseSafetyError, match="allowlist"):
            validate_test_database_url(url)


def test_safety_validator_accepts_allowlisted_database():
    """7. Accepts strictly the allowlisted database name fashion_marketplace_test."""
    valid_url = "postgresql://user:pass@localhost:5432/fashion_marketplace_test"
    dev_url = "postgresql://user:pass@localhost:5432/fashion_marketplace_dev"
    result = validate_test_database_url(valid_url, dev_url=dev_url)
    assert result == valid_url

    # Case-insensitive acceptance
    upper_url = "postgresql://user:pass@localhost:5432/FASHION_MARKETPLACE_TEST"
    assert validate_test_database_url(upper_url, dev_url=dev_url) == upper_url


def test_verify_active_database_rejects_unexpected_live_database():
    """8. Post-connection check aborts immediately if current_database() is not fashion_marketplace_test."""
    class FakeConnection:
        def __init__(self, db_name):
            self.db_name = db_name

        def scalar(self, stmt):
            return self.db_name

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeEngine:
        def __init__(self, db_name):
            self.db_name = db_name

        def connect(self):
            return FakeConnection(self.db_name)

    fake_dev: Any = FakeEngine("fashion_marketplace_dev")
    fake_random: Any = FakeEngine("random_database")
    fake_none: Any = FakeEngine(None)

    # Rejects dev database
    with pytest.raises(DatabaseSafetyError, match="fashion_marketplace_dev"):
        verify_active_database(fake_dev)

    # Rejects any other database name not in allowlist
    with pytest.raises(DatabaseSafetyError, match="allowlist"):
        verify_active_database(fake_random)

    # Rejects null database return
    with pytest.raises(DatabaseSafetyError, match="Unable to query active database"):
        verify_active_database(fake_none)


def test_verify_active_database_accepts_allowlisted_name():
    """9. Post-connection check succeeds when active database matches fashion_marketplace_test."""
    class FakeConnection:
        def scalar(self, stmt):
            return ALLOWED_TEST_DATABASE_NAME

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    fake_allowed: Any = FakeEngine()
    assert verify_active_database(fake_allowed) == ALLOWED_TEST_DATABASE_NAME


def test_apply_migrations_fails_early_if_not_in_allowlist():
    """10. Migration check fails before any Alembic command is executed if URL is not in allowlist."""
    with pytest.raises(DatabaseSafetyError, match="allowlist"):
        apply_test_migrations("postgresql://user:pass@localhost:5432/unauthorized_db")


# =========================================================================== #
# Fixtures for Real PostgreSQL Session
# =========================================================================== #

@pytest.fixture(scope="session")
def postgres_engine():
    """Create a validated engine for the PostgreSQL test database."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    dev_url = os.environ.get("DATABASE_URL")
    validated_url = validate_test_database_url(test_url, dev_url)
    engine = create_safe_test_engine(validated_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def PostgresSessionLocal(postgres_engine):
    return sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def configure_payment_recipient(monkeypatch):
    """Ensure test environment configures recipient account matching payment slips."""
    monkeypatch.setattr(settings, "PAYMENT_RECIPIENT_ACCOUNT", "012-3-45678-9")


@pytest.fixture
def pg_session(PostgresSessionLocal):
    """Provide a clean PostgreSQL session with row cleanup before and after each test."""
    session = PostgresSessionLocal()
    clean_test_database_rows(session)
    try:
        yield session
    finally:
        session.rollback()
        clean_test_database_rows(session)
        session.close()


@pytest.fixture
def pg_client(pg_session):
    def _override_get_db():
        try:
            yield pg_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================== #
# 1. PostgreSQL Auth Lifecycle
# =========================================================================== #

@postgres_required
def test_postgres_auth_lifecycle(pg_client, pg_session):
    # Register
    reg_resp = pg_client.post(
        "/api/auth/register",
        json={"email": "pg_user@fashion.com", "password": "SecurePassword123!", "role": "buyer"},
    )
    assert reg_resp.status_code == 200
    user_id = reg_resp.json()["id"]

    # Verify directly in PostgreSQL table
    user = pg_session.get(User, user_id)
    assert user is not None
    assert user.email == "pg_user@fashion.com"

    # Login
    login_resp = pg_client.post(
        "/api/auth/login",
        json={"email": "pg_user@fashion.com", "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Authenticated me endpoint
    me_resp = pg_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "pg_user@fashion.com"


# =========================================================================== #
# 2. Concurrency Safety: Same Order Duplicate Fulfillment
# =========================================================================== #

@postgres_required
def test_postgres_concurrent_fulfillment_same_order(postgres_engine, PostgresSessionLocal):
    """Test SELECT ... FOR UPDATE row-locking prevents duplicate fulfillment of the same order."""
    init_session = PostgresSessionLocal()
    clean_test_database_rows(init_session)
    now = datetime.now(timezone.utc)

    # Seed Seller, Buyer, Product, Stock
    seller = User(id="pg-s-1", email="pg_s1@test.com", password_hash="h", role="seller", created_at=now, updated_at=now)
    buyer = User(id="pg-b-1", email="pg_b1@test.com", password_hash="h", role="buyer", created_at=now, updated_at=now)
    prod = Product(id="pg-p-1", name="Jacket", description="d", price=Decimal("100.00"), stock_quantity=10, category="Coats", seller_id="pg-s-1", is_active=True)
    stk = Stock(id="pg-stk-1", product_id="pg-p-1", variant_key="L", available_quantity=10, updated_at=now)
    ord1 = Order(id="pg-ord-1", user_id="pg-b-1", status="PENDING_PAYMENT", total_amount=Decimal("100.00"), created_at=now, updated_at=now)
    ord1.items.append(OrderItem(id="pg-item-1", product_id="pg-p-1", stock_id="pg-stk-1", variant_key="L", quantity=1, unit_price=Decimal("100.00")))
    pay1 = Payment(id="pg-pay-1", order_id="pg-ord-1", payment_type="BANK_TRANSFER", slip_reference="slip-1", slip_status="UPLOADED", verification_status="UNAVAILABLE", created_at=now)

    init_session.add_all([seller, buyer, prod, stk, ord1, pay1])
    init_session.commit()
    init_session.close()

    trusted_result = {
        "verified": True,
        "amount": "100.00",
        "destination_account": "012-3-45678-9",
        "reference": "BANK-REF-999",
    }

    results = []

    def _fulfill_task(worker_id):
        session = PostgresSessionLocal()
        try:
            res = verify_payment_and_decrement_stock_db(
                session,
                "pg-ord-1",
                "pg-pay-1",
                "slip-1",
                verification_result=trusted_result,
            )
            results.append((worker_id, res))
        finally:
            session.close()

    # Launch 2 concurrent workers attempting fulfillment simultaneously on separate PostgreSQL connections
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_fulfill_task, 1)
        f2 = executor.submit(_fulfill_task, 2)
        f1.result()
        f2.result()

    verify_session = PostgresSessionLocal()
    updated_order = verify_session.get(Order, "pg-ord-1")
    updated_stock = verify_session.get(Stock, "pg-stk-1")
    shipments = verify_session.scalars(select(Shipment).where(Shipment.order_id == "pg-ord-1")).all()

    # Order must be PAID
    assert updated_order.status == "PAID"
    # Stock must have been decremented exactly ONCE (from 10 to 9)
    assert updated_stock.available_quantity == 9
    # Exactly ONE shipment must have been created
    assert len(shipments) == 1

    verify_session.close()


# =========================================================================== #
# 3. Concurrency Safety: Competing for the Last Stock Item
# =========================================================================== #

@postgres_required
def test_postgres_concurrent_stock_deduction_last_item(postgres_engine, PostgresSessionLocal):
    """Test that two concurrent orders competing for the last 1 stock item never oversell."""
    init_session = PostgresSessionLocal()
    clean_test_database_rows(init_session)
    now = datetime.now(timezone.utc)

    seller = User(id="pg-s-2", email="pg_s2@test.com", password_hash="h", role="seller", created_at=now, updated_at=now)
    buyer1 = User(id="pg-b-2a", email="pg_b2a@test.com", password_hash="h", role="buyer", created_at=now, updated_at=now)
    buyer2 = User(id="pg-b-2b", email="pg_b2b@test.com", password_hash="h", role="buyer", created_at=now, updated_at=now)
    prod = Product(id="pg-p-2", name="Silk Scarf", description="d", price=Decimal("50.00"), stock_quantity=1, category="Accessories", seller_id="pg-s-2", is_active=True)
    stk = Stock(id="pg-stk-2", product_id="pg-p-2", variant_key="ONE", available_quantity=1, updated_at=now)

    ord_a = Order(id="pg-ord-2a", user_id="pg-b-2a", status="PENDING_PAYMENT", total_amount=Decimal("50.00"), created_at=now, updated_at=now)
    ord_a.items.append(OrderItem(id="pg-item-2a", product_id="pg-p-2", stock_id="pg-stk-2", variant_key="ONE", quantity=1, unit_price=Decimal("50.00")))
    pay_a = Payment(id="pg-pay-2a", order_id="pg-ord-2a", payment_type="BANK_TRANSFER", slip_reference="slip-2a", slip_status="UPLOADED", verification_status="UNAVAILABLE", created_at=now)

    ord_b = Order(id="pg-ord-2b", user_id="pg-b-2b", status="PENDING_PAYMENT", total_amount=Decimal("50.00"), created_at=now, updated_at=now)
    ord_b.items.append(OrderItem(id="pg-item-2b", product_id="pg-p-2", stock_id="pg-stk-2", variant_key="ONE", quantity=1, unit_price=Decimal("50.00")))
    pay_b = Payment(id="pg-pay-2b", order_id="pg-ord-2b", payment_type="BANK_TRANSFER", slip_reference="slip-2b", slip_status="UPLOADED", verification_status="UNAVAILABLE", created_at=now)

    init_session.add_all([seller, buyer1, buyer2, prod, stk, ord_a, pay_a, ord_b, pay_b])
    init_session.commit()
    init_session.close()

    trusted_result = {
        "verified": True,
        "amount": "50.00",
        "destination_account": "012-3-45678-9",
        "reference": "BANK-REF-COMPETE",
    }

    def _fulfill_order(order_id, payment_id, slip_ref):
        session = PostgresSessionLocal()
        try:
            return verify_payment_and_decrement_stock_db(
                session,
                order_id,
                payment_id,
                slip_ref,
                verification_result=trusted_result,
            )
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_a = executor.submit(_fulfill_order, "pg-ord-2a", "pg-pay-2a", "slip-2a")
        f_b = executor.submit(_fulfill_order, "pg-ord-2b", "pg-pay-2b", "slip-2b")
        res_a = f_a.result()
        res_b = f_b.result()

    verify_session = PostgresSessionLocal()
    final_stk = verify_session.get(Stock, "pg-stk-2")
    final_prod = verify_session.get(Product, "pg-p-2")
    final_ord_a = verify_session.get(Order, "pg-ord-2a")
    final_ord_b = verify_session.get(Order, "pg-ord-2b")

    # Available quantity must NEVER be negative (must be exactly 0)
    assert final_stk.available_quantity == 0
    assert final_prod.stock_quantity == 0

    # Exactly ONE order must be PAID, and the other must be MANUAL_RESOLUTION_REQUIRED
    statuses = {final_ord_a.status, final_ord_b.status}
    assert statuses == {"PAID", "MANUAL_RESOLUTION_REQUIRED"}

    verify_session.close()


# =========================================================================== #
# 4. Payment Verification Unavailable & Succeeded Logic
# =========================================================================== #

@postgres_required
def test_postgres_payment_unavailable_flow(pg_session):
    now = datetime.now(timezone.utc)
    seller = User(id="pg-s-3", email="pg_s3@test.com", password_hash="h", role="seller", created_at=now, updated_at=now)
    buyer = User(id="pg-b-3", email="pg_b3@test.com", password_hash="h", role="buyer", created_at=now, updated_at=now)
    prod = Product(id="pg-p-3", name="Shirt", description="d", price=Decimal("40.00"), stock_quantity=5, category="Shirts", seller_id="pg-s-3", is_active=True)
    stk = Stock(id="pg-stk-3", product_id="pg-p-3", variant_key="M", available_quantity=5, updated_at=now)
    ord1 = Order(id="pg-ord-3", user_id="pg-b-3", status="PENDING_PAYMENT", total_amount=Decimal("40.00"), created_at=now, updated_at=now)
    ord1.items.append(OrderItem(id="pg-item-3", product_id="pg-p-3", stock_id="pg-stk-3", variant_key="M", quantity=1, unit_price=Decimal("40.00")))
    pay1 = Payment(id="pg-pay-3", order_id="pg-ord-3", payment_type="BANK_TRANSFER", slip_reference="slip-3", slip_status="UPLOADED", verification_status="UNAVAILABLE", created_at=now)

    pg_session.add_all([seller, buyer, prod, stk, ord1, pay1])
    pg_session.commit()

    # Unavailable verification (None)
    res = verify_payment_and_decrement_stock_db(pg_session, "pg-ord-3", "pg-pay-3", "slip-3", verification_result=None)
    assert res["success"] is False
    assert "unavailable" in res["message"].lower()

    pg_session.refresh(ord1)
    pg_session.refresh(stk)
    pg_session.refresh(pay1)

    assert ord1.status == "PENDING_PAYMENT"
    assert stk.available_quantity == 5
    assert pay1.verification_status == "UNAVAILABLE"
    shipments = pg_session.scalars(select(Shipment).where(Shipment.order_id == "pg-ord-3")).all()
    assert len(shipments) == 0


# =========================================================================== #
# 5. Idempotent Retry & Support Tickets
# =========================================================================== #

@postgres_required
def test_postgres_support_ticket_idempotency(pg_client, pg_session):
    now = datetime.now(timezone.utc)
    seller = User(id="pg-s-4", email="pg_s4@test.com", password_hash="h", role="seller", created_at=now, updated_at=now)
    buyer = User(id="pg-b-4", email="pg_b4@test.com", password_hash="h", role="buyer", created_at=now, updated_at=now)
    ord1 = Order(id="pg-ord-4", user_id="pg-b-4", status="PAID", total_amount=Decimal("30.00"), created_at=now, updated_at=now)
    shp1 = Shipment(id="pg-shp-4", order_id="pg-ord-4", carrier_name="FashionExpress", tracking_number="FE-PG-100", status="PREPARING", estimated_delivery=now, created_at=now)
    pg_session.add_all([seller, buyer, ord1, shp1])
    pg_session.commit()

    token = create_access_token({"sub": "pg_b4@test.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # First logistics check creates ticket
    resp1 = pg_client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-PG-100"}, headers=headers)
    assert resp1.status_code == 200
    ticket_id = resp1.json()["ticket_id"]
    assert resp1.json()["ticket_created"] is True

    # Second logistics check detects ticket and does not duplicate
    resp2 = pg_client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-PG-100"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["ticket_created"] is False
    assert resp2.json()["ticket_id"] == ticket_id

    # Verify only 1 ticket in database
    tickets = pg_session.scalars(select(SupportTicket).where(SupportTicket.order_id == "pg-ord-4")).all()
    assert len(tickets) == 1
