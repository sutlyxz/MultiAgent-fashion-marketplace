"""Unit tests for Phase D: Payment Attempts, Verification, and Atomic Stock Deduction.

All tests use FastAPI TestClient and an isolated SQLite in-memory database
by overriding the `get_db` dependency. No live or dev database is touched.
"""

from datetime import datetime, timezone
from decimal import Decimal
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
from app.config import settings
from app.db_connection import Base, get_db
from app.main import app
from app.models import Order, OrderItem, Payment, Product, Shipment, Stock, User
from app.routers.orders import verify_payment_and_decrement_stock_db


@pytest.fixture
def test_db_session(monkeypatch):
    """Create an isolated SQLite in-memory database and populate test seed data."""
    monkeypatch.setattr(settings, "PAYMENT_RECIPIENT_ACCOUNT", "recipient-12345")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    # 1. Seed Users (Buyer 1, Buyer 2, Seller)
    buyer1 = User(
        id="usr-pay-buyer1",
        email="buyer_pay_1@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    buyer2 = User(
        id="usr-pay-buyer2",
        email="buyer_pay_2@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    seller = User(
        id="usr-pay-seller",
        email="seller_pay@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add_all([buyer1, buyer2, seller])
    session.flush()

    # 2. Seed Product
    product = Product(
        id="prod-pay-100",
        name="Payment Test Jacket",
        description="Jacket for payment tests",
        price=Decimal("100.00"),
        stock_quantity=10,
        category="Jackets",
        seller_id="usr-pay-seller",
        is_active=True,
    )
    session.add(product)
    session.flush()

    # 3. Seed Stock Variant
    stock = Stock(
        id="stk-pay-101",
        product_id="prod-pay-100",
        variant_key="L",
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
def buyer1_token():
    return create_access_token({"sub": "buyer_pay_1@fashion.com"})


@pytest.fixture
def buyer2_token():
    return create_access_token({"sub": "buyer_pay_2@fashion.com"})


def test_upload_slip_creates_payment_attempt(client, buyer1_token, test_db_session):
    """1. Uploading a slip creates a new Payment attempt row in PostgreSQL."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 1}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-001"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["order_id"] == order_id
    assert "payment_id" in data
    assert data["slip_status"] == "UPLOADED"
    assert data["verification_status"] == "UNAVAILABLE"

    # Verify payment attempt in DB
    payment = test_db_session.get(Payment, data["payment_id"])
    assert payment is not None
    assert payment.order_id == order_id
    assert payment.slip_reference == "REF-SLIP-001"


def test_multiple_slip_uploads_create_1_to_n_history(client, buyer1_token, test_db_session):
    """2. Multiple slip uploads for an unpaid order record separate 1:N payment attempts."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 1}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    # First slip upload
    res1 = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-FIRST"},
        headers=headers,
    )
    p1_id = res1.json()["payment_id"]

    # Second slip upload
    res2 = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-SECOND"},
        headers=headers,
    )
    p2_id = res2.json()["payment_id"]

    assert p1_id != p2_id

    # Verify 2 payment rows exist in DB under same order_id
    payments = test_db_session.scalars(
        select(Payment).where(Payment.order_id == order_id)
    ).all()
    assert len(payments) == 2
    refs = {p.slip_reference for p in payments}
    assert refs == {"REF-SLIP-FIRST", "REF-SLIP-SECOND"}


def test_verification_unavailable_keeps_stock_and_order_unchanged(client, buyer1_token, test_db_session):
    """3. Verification Unavailable does NOT deduct stock, does NOT set PAID, and creates NO shipment."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-UNAVAIL"},
        headers=headers,
    )
    assert res.status_code == 200
    assert "unavailable" in res.json()["message"].lower()

    # Check order & stock in DB
    order = test_db_session.get(Order, order_id)
    assert order.status == "PENDING_PAYMENT"

    # Under Option A, stock was deducted by 2 at order creation (10 -> 8), and unavailable verification leaves it at 8
    stock = test_db_session.get(Stock, "stk-pay-101")
    assert stock.available_quantity == 8

    shipments = test_db_session.scalars(
        select(Shipment).where(Shipment.order_id == order_id)
    ).all()
    assert shipments == []


def test_verification_rejected_does_not_deduct_stock(client, buyer1_token, test_db_session):
    """4. Verification Rejected (mismatched amount or account) does NOT deduct stock."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-BAD"},
        headers=headers,
    )
    payment_id = upload_res.json()["payment_id"]

    # Call verify helper with mismatched amount
    bad_result = verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "REF-SLIP-BAD",
        {
            "verified": True,
            "amount": "50.00",  # Expected 200.00
            "destination_account": "recipient-12345",
        },
    )

    assert bad_result["success"] is False
    assert "failed" in bad_result["message"].lower()

    order = test_db_session.get(Order, order_id)
    assert order.status == "PENDING_PAYMENT"

    payment = test_db_session.get(Payment, payment_id)
    assert payment.verification_status == "REJECTED"

    # Under Option A, stock was deducted by 2 at order creation (10 -> 8), and rejected verification leaves it at 8
    stock = test_db_session.get(Stock, "stk-pay-101")
    assert stock.available_quantity == 8


def test_verification_succeeded_deducts_stock_and_creates_shipment(client, buyer1_token, test_db_session):
    """5 & 6. Verification Succeeded deducts stock, recalculates aggregate product stock, sets PAID, and creates Shipment."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 3}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-GOOD"},
        headers=headers,
    )
    payment_id = upload_res.json()["payment_id"]

    # Call verify helper with matching verification result
    result = verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "REF-SLIP-GOOD",
        {
            "verified": True,
            "amount": "300.00",
            "destination_account": "recipient-12345",
            "reference": "TXN-BANK-1001",
        },
    )

    assert result["success"] is True
    assert "receipt" in result

    # Check order & stock in DB
    order = test_db_session.get(Order, order_id)
    assert order.status == "PAID"

    stock = test_db_session.get(Stock, "stk-pay-101")
    assert stock.available_quantity == 7  # 10 - 3

    product = test_db_session.get(Product, "prod-pay-100")
    assert product.stock_quantity == 7  # Recalculated aggregate

    shipments = test_db_session.scalars(
        select(Shipment).where(Shipment.order_id == order_id)
    ).all()
    assert len(shipments) == 1
    assert shipments[0].status == "PREPARING"


def test_insufficient_stock_prevented_at_order_creation(client, buyer1_token, test_db_session):
    """7. Option A: Insufficient stock is rejected at order creation time, preventing overselling."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 999}]},
        headers=headers,
    )
    assert create_res.status_code == 400
    assert "Insufficient stock" in create_res.json()["detail"]

    # Stock in DB is untouched
    stock = test_db_session.get(Stock, "stk-pay-101")
    assert stock.available_quantity == 10


def test_duplicate_order_items_aggregated_at_order_creation(client, buyer1_token, test_db_session):
    """8. Option A: Duplicate items referencing same stock_id are aggregated at order creation."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # Combined req = 5 + 6 = 11 > 10 available
    res = client.post(
        "/api/orders/create",
        json={
            "items": [
                {"product_id": "prod-pay-100", "variant_key": "L", "quantity": 5},
                {"product_id": "prod-pay-100", "variant_key": "L", "quantity": 6},
            ]
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "Insufficient stock" in res.json()["detail"]

    # Stock untouched
    stock = test_db_session.get(Stock, "stk-pay-101")
    assert stock.available_quantity == 10


def test_retry_fulfilled_order_no_duplicate_deduction(client, buyer1_token, test_db_session):
    """9. Retry verification on an already fulfilled order does NOT deduct stock or create duplicate shipment."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 1}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "REF-SLIP-ONCE"},
        headers=headers,
    )
    payment_id = upload_res.json()["payment_id"]

    # Fulfill order
    verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "REF-SLIP-ONCE",
        {
            "verified": True,
            "amount": "100.00",
            "destination_account": "recipient-12345",
        },
    )

    stock_after_first = test_db_session.get(Stock, "stk-pay-101").available_quantity
    shipments_count_first = len(
        test_db_session.scalars(select(Shipment).where(Shipment.order_id == order_id)).all()
    )

    # Retry verification on same payment
    retry_result = verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "REF-SLIP-ONCE",
        {
            "verified": True,
            "amount": "100.00",
            "destination_account": "recipient-12345",
        },
    )

    assert retry_result["success"] is True
    assert "already verified" in retry_result["message"].lower()

    stock_after_second = test_db_session.get(Stock, "stk-pay-101").available_quantity
    shipments_count_second = len(
        test_db_session.scalars(select(Shipment).where(Shipment.order_id == order_id)).all()
    )

    assert stock_after_second == stock_after_first
    assert shipments_count_second == shipments_count_first == 1


def test_unauthorized_user_cannot_upload_slip(client, buyer1_token, buyer2_token):
    """12. Unauthorized user cannot upload a slip for another user's order."""
    headers1 = {"Authorization": f"Bearer {buyer1_token}"}
    headers2 = {"Authorization": f"Bearer {buyer2_token}"}

    # Buyer 1 creates order
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-pay-100", "variant_key": "L", "quantity": 1}]},
        headers=headers1,
    )
    order_id = create_res.json()["id"]

    # Buyer 2 tries to upload slip for Buyer 1's order -> 403
    res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "HACK-SLIP"},
        headers=headers2,
    )
    assert res.status_code == 403
    assert res.json() == {"detail": "You do not have permission to upload a slip for this order"}
