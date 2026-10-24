"""Unit tests for Order Creation and Order History APIs connected to PostgreSQL / SQLAlchemy.

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
from app.db_connection import Base, get_db
from app.main import app
from app.models import Order, OrderItem, Product, Stock, User


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

    # 1. Seed Users (Buyer 1, Buyer 2, Seller)
    buyer1 = User(
        id="usr-ord-buyer1",
        email="buyer_ord_1@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    buyer2 = User(
        id="usr-ord-buyer2",
        email="buyer_ord_2@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    seller = User(
        id="usr-ord-seller",
        email="seller_ord@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add_all([buyer1, buyer2, seller])
    session.flush()

    # 2. Seed Product
    product1 = Product(
        id="prod-ord-100",
        name="Designer Silk Scarf",
        description="Luxury silk scarf",
        price=Decimal("50.00"),
        stock_quantity=10,
        category="Accessories",
        seller_id="usr-ord-seller",
        is_active=True,
    )
    product2 = Product(
        id="prod-ord-200",
        name="Cotton T-Shirt",
        description="Basic white shirt",
        price=Decimal("20.00"),
        stock_quantity=5,
        category="Shirts",
        seller_id="usr-ord-seller",
        is_active=True,
    )
    session.add_all([product1, product2])
    session.flush()

    # 3. Seed Stock Variants
    stock1_m = Stock(
        id="stk-ord-101",
        product_id="prod-ord-100",
        variant_key="M",
        available_quantity=10,
        updated_at=now,
    )
    stock2_s = Stock(
        id="stk-ord-201",
        product_id="prod-ord-200",
        variant_key="S",
        available_quantity=5,
        updated_at=now,
    )
    session.add_all([stock1_m, stock2_s])
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
    return create_access_token({"sub": "buyer_ord_1@fashion.com"})


@pytest.fixture
def buyer2_token():
    return create_access_token({"sub": "buyer_ord_2@fashion.com"})


@pytest.fixture
def seller_token():
    return create_access_token({"sub": "seller_ord@fashion.com"})


def test_create_order_success(client, buyer1_token, test_db_session):
    """1. Create Order succeeds and saves order + items in database."""
    payload = {
        "items": [
            {"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2},
            {"product_id": "prod-ord-200", "variant_key": "S", "quantity": 1},
        ]
    }
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    res = client.post("/api/orders/create", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "usr-ord-buyer1"
    assert data["status"] == "PENDING_PAYMENT"
    # Total amount = (50.00 * 2) + (20.00 * 1) = 120.00
    assert data["total_amount"] == 120.00
    assert data["payment"] is None
    assert data["shipment"] is None
    assert len(data["items"]) == 2

    # Verify database persistence and foreign keys
    order_id = data["id"]
    db_order = test_db_session.get(Order, order_id)
    assert db_order is not None
    assert db_order.total_amount == Decimal("120.00")
    assert len(db_order.items) == 2

    item1 = next(i for i in db_order.items if i.product_id == "prod-ord-100")
    assert item1.stock_id == "stk-ord-101"
    assert item1.quantity == 2
    assert item1.unit_price == Decimal("50.00")


def test_create_order_empty_items_rejected(client, buyer1_token):
    """Reject empty order items with 400 error."""
    res = client.post(
        "/api/orders/create",
        json={"items": []},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 400
    assert res.json() == {"detail": "Order must contain at least one item"}


def test_create_order_nonexistent_product_or_variant(client, buyer1_token):
    """4. Non-existent Product or Stock Variant returns 404 error."""
    # Non-existent product
    res1 = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "missing-prod-999", "variant_key": "M", "quantity": 1}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res1.status_code == 404
    assert res1.json() == {"detail": "Product missing-prod-999 not found"}

    # Non-existent variant
    res2 = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "XXL", "quantity": 1}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res2.status_code == 404
    assert res2.json() == {"detail": "Variant XXL not found for product prod-ord-100"}


def test_create_order_insufficient_stock(client, buyer1_token):
    """5. Quantity exceeding available stock returns 400 error."""
    res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 999}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 400
    assert "Insufficient stock for Designer Silk Scarf (M)" in res.json()["detail"]


def test_get_my_orders_filtering(client, buyer1_token, buyer2_token):
    """7. GET /api/orders/my-orders returns ONLY current user's orders."""
    headers1 = {"Authorization": f"Bearer {buyer1_token}"}
    headers2 = {"Authorization": f"Bearer {buyer2_token}"}

    # Buyer 1 creates order
    client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1}]},
        headers=headers1,
    )

    # Buyer 2 creates order
    client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-200", "variant_key": "S", "quantity": 1}]},
        headers=headers2,
    )

    # Buyer 1 fetches my-orders -> receives only 1 order
    res1 = client.get("/api/orders/my-orders", headers=headers1)
    assert res1.status_code == 200
    orders1 = res1.json()
    assert len(orders1) == 1
    assert orders1[0]["user_id"] == "usr-ord-buyer1"

    # Buyer 2 fetches my-orders -> receives only 1 order
    res2 = client.get("/api/orders/my-orders", headers=headers2)
    assert res2.status_code == 200
    orders2 = res2.json()
    assert len(orders2) == 1
    assert orders2[0]["user_id"] == "usr-ord-buyer2"


def test_get_order_by_id_authorization(client, buyer1_token, buyer2_token, seller_token):
    """8. GET /api/orders/{id} verifies authorization correctly."""
    headers1 = {"Authorization": f"Bearer {buyer1_token}"}
    headers2 = {"Authorization": f"Bearer {buyer2_token}"}
    headers_seller = {"Authorization": f"Bearer {seller_token}"}

    # Buyer 1 creates order
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1}]},
        headers=headers1,
    )
    order_id = create_res.json()["id"]

    # Buyer 1 can view own order
    res1 = client.get(f"/api/orders/{order_id}", headers=headers1)
    assert res1.status_code == 200
    assert res1.json()["id"] == order_id

    # Seller can view order
    res_seller = client.get(f"/api/orders/{order_id}", headers=headers_seller)
    assert res_seller.status_code == 200
    assert res_seller.json()["id"] == order_id

    # Buyer 2 is forbidden from viewing Buyer 1's order
    res2 = client.get(f"/api/orders/{order_id}", headers=headers2)
    assert res2.status_code == 403
    assert res2.json() == {"detail": "You do not have permission to view this order"}

    # Missing order ID -> 404
    res_404 = client.get("/api/orders/missing-order-999", headers=headers1)
    assert res_404.status_code == 404
    assert res_404.json() == {"detail": "Order not found"}


def test_create_order_deducts_stock_immediately(client, buyer1_token, test_db_session):
    """10. Option A order creation immediately and atomically deducts stock in DB."""
    res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 3}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 200

    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 7, "Stock available_quantity must be decremented by 3"
    prod = test_db_session.get(Product, "prod-ord-100")
    assert prod.stock_quantity == 7, "Product stock_quantity must synchronize with variant sum"


def test_orders_api_does_not_depend_on_in_memory_db(client, buyer1_token, monkeypatch):
    """11. Orders API operates on DB even if in-memory db.orders is cleared."""
    from app.database import db

    monkeypatch.setattr(db, "orders", [])
    monkeypatch.setattr(db, "order_items", [])

    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert create_res.status_code == 200
    order_id = create_res.json()["id"]

    res = client.get(f"/api/orders/{order_id}", headers={"Authorization": f"Bearer {buyer1_token}"})
    assert res.status_code == 200
    assert res.json()["id"] == order_id


def test_create_order_multiple_items_deducts_each_correctly(client, buyer1_token, test_db_session):
    """Order with multiple items correctly deducts stock for each item's variant."""
    payload = {
        "items": [
            {"product_id": "prod-ord-100", "variant_key": "M", "quantity": 4},
            {"product_id": "prod-ord-200", "variant_key": "S", "quantity": 2},
        ]
    }
    res = client.post(
        "/api/orders/create",
        json=payload,
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 200

    stk1 = test_db_session.get(Stock, "stk-ord-101")
    assert stk1.available_quantity == 6  # 10 - 4
    prod1 = test_db_session.get(Product, "prod-ord-100")
    assert prod1.stock_quantity == 6

    stk2 = test_db_session.get(Stock, "stk-ord-201")
    assert stk2.available_quantity == 3  # 5 - 2
    prod2 = test_db_session.get(Product, "prod-ord-200")
    assert prod2.stock_quantity == 3


def test_create_order_insufficient_stock_rejects_and_rolls_back(client, buyer1_token, test_db_session):
    """Insufficient stock rejects order, creates no items, and modifies no stock."""
    initial_orders_count = len(test_db_session.scalars(select(Order)).all())
    initial_items_count = len(test_db_session.scalars(select(OrderItem)).all())

    res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 999}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 400
    assert "Insufficient stock" in res.json()["detail"]

    # Verify nothing was created and stock was untouched
    assert len(test_db_session.scalars(select(Order)).all()) == initial_orders_count
    assert len(test_db_session.scalars(select(OrderItem)).all()) == initial_items_count
    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 10
    prod = test_db_session.get(Product, "prod-ord-100")
    assert prod.stock_quantity == 10


def test_create_order_partial_invalid_item_no_partial_deductions(client, buyer1_token, test_db_session):
    """If one item is valid and another item is invalid (nonexistent product), no partial deductions occur."""
    payload = {
        "items": [
            {"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2},
            {"product_id": "nonexistent-product-id", "variant_key": "M", "quantity": 1},
        ]
    }
    res = client.post(
        "/api/orders/create",
        json=payload,
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert res.status_code == 404

    # The valid item's stock must NOT be altered
    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 10


def test_create_order_database_error_rolls_back_everything(client, buyer1_token, test_db_session, monkeypatch):
    """If a database error occurs during order creation, the transaction rolls back completely."""
    from sqlalchemy.exc import OperationalError

    original_commit = test_db_session.commit

    def _failing_commit():
        raise OperationalError("Simulated DB connection failure", {}, Exception("connection failed"))

    monkeypatch.setattr(test_db_session, "commit", _failing_commit)

    with pytest.raises(Exception):
        client.post(
            "/api/orders/create",
            json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
            headers={"Authorization": f"Bearer {buyer1_token}"},
        )

    # Restore commit and verify that stock was NOT deducted
    monkeypatch.setattr(test_db_session, "commit", original_commit)
    test_db_session.expire_all()
    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 10


def test_concurrent_orders_cannot_oversell(client, buyer1_token, buyer2_token, test_db_session):
    """Concurrent orders competing for limited stock cannot oversell."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    # Set prod-ord-100 stock to exactly 1
    stk = test_db_session.get(Stock, "stk-ord-101")
    stk.available_quantity = 1
    prod = test_db_session.get(Product, "prod-ord-100")
    prod.stock_quantity = 1
    test_db_session.commit()

    results = []
    lock = threading.Lock()

    def _place_order(token):
        with lock:
            res = client.post(
                "/api/orders/create",
                json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1}]},
                headers={"Authorization": f"Bearer {token}"},
            )
            results.append(res.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_place_order, buyer1_token)
        f2 = executor.submit(_place_order, buyer2_token)
        f1.result()
        f2.result()

    # Exactly 1 order must succeed (200), and the other must fail (400)
    assert sorted(results) == [200, 400]

    test_db_session.expire_all()
    final_stk = test_db_session.get(Stock, "stk-ord-101")
    assert final_stk.available_quantity == 0
    final_prod = test_db_session.get(Product, "prod-ord-100")
    assert final_prod.stock_quantity == 0


def test_payment_verification_does_not_deduct_stock_second_time(client, buyer1_token, test_db_session, monkeypatch):
    """Payment verification confirms order and creates shipment without deducting stock a second time."""
    from app.config import settings
    from app.routers.orders import verify_payment_and_decrement_stock_db

    monkeypatch.setattr(settings, "PAYMENT_RECIPIENT_ACCOUNT", "recipient-bank-acc")

    # 1. Create order for 3 items (stock was 10 -> becomes 7)
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 3}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert create_res.status_code == 200
    order_id = create_res.json()["id"]

    stk_after_order = test_db_session.get(Stock, "stk-ord-101").available_quantity
    assert stk_after_order == 7

    # 2. Upload slip
    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "SLIP-OPTION-A"},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    payment_id = upload_res.json()["payment_id"]

    # 3. Verify payment
    verify_res = verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "SLIP-OPTION-A",
        {
            "verified": True,
            "amount": "150.00",  # 50.00 * 3
            "destination_account": "recipient-bank-acc",
            "reference": "BANK-TXN-001",
        },
    )
    assert verify_res["success"] is True

    # 4. Stock must STILL be 7, NOT 4!
    test_db_session.expire_all()
    stk_after_payment = test_db_session.get(Stock, "stk-ord-101").available_quantity
    assert stk_after_payment == 7
    order_after_payment = test_db_session.get(Order, order_id)
    assert order_after_payment.status == "PAID"


def test_buyer_can_cancel_own_unpaid_order_and_restores_stock(client, buyer1_token, test_db_session):
    """1, 2, 3: Buyer cancels own unpaid order, variant stock increases by ordered qty, product stock synchronizes."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers=headers,
    )
    assert create_res.status_code == 200
    order_id = create_res.json()["id"]

    # Post-order: stock is 8, prod is 8
    test_db_session.expire_all()
    stk = test_db_session.get(Stock, "stk-ord-101")
    prod = test_db_session.get(Product, "prod-ord-100")
    assert stk.available_quantity == 8
    assert prod.stock_quantity == 8

    # Cancel order
    cancel_res = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["id"] == order_id
    assert cancel_data["status"] == "CANCELLED"

    # Stock is restored back to 10
    test_db_session.expire_all()
    stk = test_db_session.get(Stock, "stk-ord-101")
    prod = test_db_session.get(Product, "prod-ord-100")
    assert stk.available_quantity == 10
    assert prod.stock_quantity == 10


def test_second_cancellation_is_idempotent_no_duplicate_stock_restoration(client, buyer1_token, test_db_session):
    """4: Second cancellation is idempotent and does not restore stock twice."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    # First cancel
    res1 = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "CANCELLED"

    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 10

    # Second cancel
    res2 = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "CANCELLED"

    test_db_session.expire_all()
    # Stock must still be 10, NOT 12!
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 10
    assert test_db_session.get(Product, "prod-ord-100").stock_quantity == 10


def test_another_buyer_cannot_cancel_order(client, buyer1_token, buyer2_token, test_db_session):
    """5: Another buyer cannot cancel the order; returns 404 to avoid leaking existence."""
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    order_id = create_res.json()["id"]

    # Buyer 2 attempts cancel
    cancel_res = client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {buyer2_token}"},
    )
    assert cancel_res.status_code == 404
    assert "not found" in cancel_res.json()["detail"].lower()

    # Stock is unchanged (remains deducted at 8)
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 8


def test_unauthenticated_user_cannot_cancel_order(client, buyer1_token, test_db_session):
    """6: Unauthenticated user cannot cancel order."""
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    order_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 401

    # Stock unchanged
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 8


def test_paid_order_cannot_be_cancelled(client, buyer1_token, test_db_session):
    """7: Paid orders cannot be cancelled through cancel endpoint."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    # Mark order as PAID in DB
    order = test_db_session.get(Order, order_id)
    order.status = "PAID"
    test_db_session.commit()

    cancel_res = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 400
    assert "paid" in cancel_res.json()["detail"].lower()

    # Stock unchanged (remains 8)
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 8


def test_invalid_nonexistent_order_id_returns_not_found(client, buyer1_token):
    """8: Invalid/nonexistent order ID returns 404 Not Found."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    cancel_res = client.post("/api/orders/nonexistent-order-id-999/cancel", headers=headers)
    assert cancel_res.status_code == 404
    assert "not found" in cancel_res.json()["detail"].lower()


def test_cancel_multiple_items_restores_all_variants_correctly(client, buyer1_token, test_db_session):
    """11: Orders with multiple items restore all affected variants and products correctly."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={
            "items": [
                {"product_id": "prod-ord-100", "variant_key": "M", "quantity": 3},
                {"product_id": "prod-ord-200", "variant_key": "S", "quantity": 2},
            ]
        },
        headers=headers,
    )
    assert create_res.status_code == 200
    order_id = create_res.json()["id"]

    # Stock after order: stk-101: 10 - 3 = 7, stk-201: 5 - 2 = 3
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 7
    assert test_db_session.get(Stock, "stk-ord-201").available_quantity == 3
    assert test_db_session.get(Product, "prod-ord-100").stock_quantity == 7
    assert test_db_session.get(Product, "prod-ord-200").stock_quantity == 3

    # Cancel order
    cancel_res = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Both stocks restored: 7 + 3 = 10, 3 + 2 = 5
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 10
    assert test_db_session.get(Stock, "stk-ord-201").available_quantity == 5
    assert test_db_session.get(Product, "prod-ord-100").stock_quantity == 10
    assert test_db_session.get(Product, "prod-ord-200").stock_quantity == 5


def test_cancellation_midway_failure_rolls_back_everything(client, buyer1_token, test_db_session, monkeypatch):
    """9: Database error midway through restoration rolls back stock and status changes."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 8

    # Simulate database error on Session.execute during stock restoration
    orig_execute = test_db_session.execute

    def flaky_execute(stmt, *args, **kwargs):
        # Fail when executing the update statement on Stock
        if "stocks" in str(stmt).lower() and "update" in str(stmt).lower():
            raise RuntimeError("Simulated DB connection drop during stock restoration")
        return orig_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(test_db_session, "execute", flaky_execute)

    with pytest.raises(RuntimeError, match="Simulated DB connection drop"):
        client.post(f"/api/orders/{order_id}/cancel", headers=headers)

    monkeypatch.undo()

    test_db_session.expire_all()
    order = test_db_session.get(Order, order_id)
    assert order.status == "PENDING_PAYMENT"
    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 8
    prod = test_db_session.get(Product, "prod-ord-100")
    assert prod.stock_quantity == 8


def test_cancellation_racing_with_payment_verification_cannot_produce_inconsistent_state(
    client, buyer1_token, test_db_session, monkeypatch
):
    """10: Cancellation racing with payment verification: cancelled order rejects verification."""
    from app.config import settings
    from app.routers.orders import verify_payment_and_decrement_stock_db

    monkeypatch.setattr(settings, "PAYMENT_RECIPIENT_ACCOUNT", "recipient-bank-acc")
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # 1. Create order
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 2}]},
        headers=headers,
    )
    order_id = create_res.json()["id"]

    # 2. Upload slip
    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id, "slip_reference": "SLIP-RACE-001"},
        headers=headers,
    )
    payment_id = upload_res.json()["payment_id"]

    # 3. Buyer cancels order first
    cancel_res = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Stock is back to 10
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 10

    # 4. Payment verification arrives later on the cancelled order
    verify_res = verify_payment_and_decrement_stock_db(
        test_db_session,
        order_id,
        payment_id,
        "SLIP-RACE-001",
        {
            "verified": True,
            "amount": "100.00",
            "destination_account": "recipient-bank-acc",
            "reference": "BANK-TXN-RACE",
        },
    )
    # Must fail because order is cancelled!
    assert verify_res["success"] is False
    assert "cancelled" in verify_res["message"].lower()

    # Stock must STILL be 10!
    test_db_session.expire_all()
    assert test_db_session.get(Stock, "stk-ord-101").available_quantity == 10
    order = test_db_session.get(Order, order_id)
    assert order.status == "CANCELLED"


# ---------------------------------------------------------------------------
# FR-02: Prevent Sellers from Purchasing Their Own Products
# ---------------------------------------------------------------------------

def test_seller_cannot_purchase_own_product(client, seller_token, test_db_session):
    """Sellers cannot create an order containing items from their own boutique."""
    # usr-ord-seller owns prod-ord-100
    res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1}]},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert res.status_code == 400
    assert "Sellers cannot purchase their own products" in res.json()["detail"]

    # Stock must NOT be decremented
    test_db_session.expire_all()
    stk = test_db_session.get(Stock, "stk-ord-101")
    assert stk.available_quantity == 10

    # No order should have been created
    orders = test_db_session.query(Order).filter(Order.user_id == "usr-ord-seller").all()
    assert len(orders) == 0


def test_multi_item_order_aborts_completely_if_any_item_is_sellers_own(client, seller_token, test_db_session):
    """If an order contains both other sellers' products and the seller's own product,

    the entire order is rejected, zero orders created, and zero stocks decremented.
    """
    now = datetime.now(timezone.utc)
    # Seed a 2nd seller and product
    seller2 = User(
        id="usr-ord-seller2",
        email="seller2_ord@fashion.com",
        password_hash="pw",
        role="seller",
        created_at=now,
        updated_at=now,
    )
    prod_other = Product(
        id="prod-ord-other",
        name="Artisan Wool Scarf",
        description="Handmade scarf",
        price=Decimal("40.00"),
        stock_quantity=5,
        category="Accessories",
        seller_id="usr-ord-seller2",
        is_active=True,
    )
    stock_other = Stock(
        id="stk-ord-other",
        product_id="prod-ord-other",
        variant_key="OneSize",
        available_quantity=5,
        updated_at=now,
    )
    test_db_session.add_all([seller2, prod_other, stock_other])
    test_db_session.commit()

    # usr-ord-seller tries to buy prod-ord-other (from seller2) AND prod-ord-100 (own product)
    res = client.post(
        "/api/orders/create",
        json={
            "items": [
                {"product_id": "prod-ord-other", "variant_key": "OneSize", "quantity": 1},
                {"product_id": "prod-ord-100", "variant_key": "M", "quantity": 1},
            ]
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert res.status_code == 400
    assert "Sellers cannot purchase their own products" in res.json()["detail"]

    # Verify BOTH stocks remain completely untouched
    test_db_session.expire_all()
    stk1 = test_db_session.get(Stock, "stk-ord-101")
    stk_oth = test_db_session.get(Stock, "stk-ord-other")
    assert stk1.available_quantity == 10
    assert stk_oth.available_quantity == 5

    # Zero orders created for usr-ord-seller
    orders = test_db_session.query(Order).filter(Order.user_id == "usr-ord-seller").all()
    assert len(orders) == 0



