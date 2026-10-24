"""Integration tests for Phase 4.5 Seller Orders & Shipment Management API.

Tests:
1. Authentication & Role (401 unauthenticated, 403 non-seller).
2. IDOR Prevention (Seller A cannot manage Seller B's shipments -> 403).
3. Nonexistent order handling (404).
4. Order State Gate (Cannot update shipment if order is not PAID -> 400).
5. Shipment Status Transitions & Validations:
   - PREPARING -> DISPATCHED requires non-empty carrier_name and tracking_number.
   - Whitespace tracking/carrier numbers are rejected.
   - DELIVERED is terminal and rejects any further mutations.
6. Data Masking on GET /api/seller/orders (multi-seller order only exposes caller's own items).
7. Multi-seller payment creation creates 1 shipment per seller with status=PREPARING and tracking=None.
8. Single dict shipment (6 keys) and shipments list backward compatibility.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token, hash_password
from app.db_connection import Base, get_db
from app.main import app
from app.models import Order, OrderItem, Payment, Product, Shipment, Stock, User


BASE_TIME = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
SELLER_A_EMAIL = "seller_a@fashion.com"
SELLER_B_EMAIL = "seller_b@fashion.com"
BUYER_EMAIL = "buyer_test@fashion.com"


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    # Create users
    seller_a = User(
        id="usr-seller-a",
        email=SELLER_A_EMAIL,
        password_hash=hash_password("Pass123!"),
        role="seller",
        name="Seller A",
        store_name="Boutique A",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    seller_b = User(
        id="usr-seller-b",
        email=SELLER_B_EMAIL,
        password_hash=hash_password("Pass123!"),
        role="seller",
        name="Seller B",
        store_name="Boutique B",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    buyer = User(
        id="usr-buyer-1",
        email=BUYER_EMAIL,
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add_all([seller_a, seller_b, buyer])
    db_session.flush()

    # Create products for each seller
    prod_a = Product(
        id="prod-a",
        name="Silk Blouse",
        description="Luxury silk",
        price=Decimal("100.00"),
        stock_quantity=10,
        category="Blouses",
        seller_id="usr-seller-a",
        is_active=True,
    )
    prod_b = Product(
        id="prod-b",
        name="Wool Trousers",
        description="Tailored wool",
        price=Decimal("150.00"),
        stock_quantity=10,
        category="Trousers",
        seller_id="usr-seller-b",
        is_active=True,
    )
    db_session.add_all([prod_a, prod_b])
    db_session.flush()

    # Stocks
    stk_a = Stock(
        id="stk-a",
        product_id="prod-a",
        variant_key="M",
        available_quantity=10,
        updated_at=BASE_TIME,
    )
    stk_b = Stock(
        id="stk-b",
        product_id="prod-b",
        variant_key="32",
        available_quantity=10,
        updated_at=BASE_TIME,
    )
    db_session.add_all([stk_a, stk_b])
    db_session.flush()

    # Order 1: Multi-seller order (PAID) containing items from Seller A and Seller B
    order_multi = Order(
        id="ord-multi-101",
        user_id="usr-buyer-1",
        status="PAID",
        total_amount=Decimal("250.00"),
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    oi_a = OrderItem(
        id="oi-multi-a",
        order_id="ord-multi-101",
        product_id="prod-a",
        stock_id="stk-a",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("100.00"),
    )
    oi_b = OrderItem(
        id="oi-multi-b",
        order_id="ord-multi-101",
        product_id="prod-b",
        stock_id="stk-b",
        variant_key="32",
        quantity=1,
        unit_price=Decimal("150.00"),
    )
    order_multi.items.extend([oi_a, oi_b])
    db_session.add(order_multi)

    # Pre-create shipments for multi-seller order
    shp_a = Shipment(
        id="shp-ord-multi-a",
        order_id="ord-multi-101",
        seller_id="usr-seller-a",
        carrier_name="Standard Delivery",
        tracking_number=None,
        status="PREPARING",
        estimated_delivery=BASE_TIME + timedelta(days=3),
        created_at=BASE_TIME,
    )
    shp_b = Shipment(
        id="shp-ord-multi-b",
        order_id="ord-multi-101",
        seller_id="usr-seller-b",
        carrier_name="Standard Delivery",
        tracking_number=None,
        status="PREPARING",
        estimated_delivery=BASE_TIME + timedelta(days=3),
        created_at=BASE_TIME,
    )
    db_session.add_all([shp_a, shp_b])

    # Order 2: Seller A only, but PENDING_PAYMENT
    order_pending = Order(
        id="ord-pending-102",
        user_id="usr-buyer-1",
        status="PENDING_PAYMENT",
        total_amount=Decimal("100.00"),
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    oi_pending = OrderItem(
        id="oi-pending-a",
        order_id="ord-pending-102",
        product_id="prod-a",
        stock_id="stk-a",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("100.00"),
    )
    order_pending.items.append(oi_pending)
    db_session.add(order_pending)

    db_session.commit()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


@pytest.fixture
def client(session):
    def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seller_a_headers():
    token = create_access_token({"sub": SELLER_A_EMAIL})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seller_b_headers():
    token = create_access_token({"sub": SELLER_B_EMAIL})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def buyer_headers():
    token = create_access_token({"sub": BUYER_EMAIL})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_seller_shipment_unauthenticated_returns_401(client):
    res_list = client.get("/api/seller/orders")
    assert res_list.status_code == 401

    res_patch = client.patch("/api/seller/orders/ord-multi-101/shipment", json={"status": "DISPATCHED"})
    assert res_patch.status_code == 401


def test_seller_shipment_forbidden_for_buyer(client, buyer_headers):
    res_list = client.get("/api/seller/orders", headers=buyer_headers)
    assert res_list.status_code == 403

    res_patch = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=buyer_headers,
        json={"status": "DISPATCHED"},
    )
    assert res_patch.status_code == 403


def test_seller_orders_data_masking(client, seller_a_headers, seller_b_headers):
    # Seller A checks orders
    resp_a = client.get("/api/seller/orders", headers=seller_a_headers)
    assert resp_a.status_code == 200
    orders_a = resp_a.json()
    assert len(orders_a) >= 1

    multi_a = next(o for o in orders_a if o["id"] == "ord-multi-101")
    # Must only see Seller A's items
    item_ids_a = [item["product_id"] for item in multi_a["items"]]
    assert item_ids_a == ["prod-a"]
    assert "prod-b" not in item_ids_a

    # Shipment data in Seller A's view must belong to Seller A
    assert multi_a["shipment"]["seller_id"] == "usr-seller-a"

    # Seller B checks orders
    resp_b = client.get("/api/seller/orders", headers=seller_b_headers)
    assert resp_b.status_code == 200
    orders_b = resp_b.json()
    multi_b = next(o for o in orders_b if o["id"] == "ord-multi-101")
    item_ids_b = [item["product_id"] for item in multi_b["items"]]
    assert item_ids_b == ["prod-b"]
    assert "prod-a" not in item_ids_b
    assert multi_b["shipment"]["seller_id"] == "usr-seller-b"


def test_seller_cannot_update_nonexistent_order(client, seller_a_headers):
    res = client.patch(
        "/api/seller/orders/ord-does-not-exist/shipment",
        headers=seller_a_headers,
        json={"status": "DISPATCHED", "carrier_name": "DHL", "tracking_number": "TRK-999"},
    )
    assert res.status_code == 404
    assert "Order not found" in res.json()["detail"]


def test_seller_idor_defense_cannot_update_other_seller_order(client, session, seller_b_headers):
    # Order 3 belongs ONLY to Seller A
    order_a_only = Order(
        id="ord-a-only-103",
        user_id="usr-buyer-1",
        status="PAID",
        total_amount=Decimal("100.00"),
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    order_a_only.items.append(
        OrderItem(
            id="oi-a-only",
            order_id="ord-a-only-103",
            product_id="prod-a",
            stock_id="stk-a",
            variant_key="M",
            quantity=1,
            unit_price=Decimal("100.00"),
        )
    )
    session.add(order_a_only)
    session.commit()

    # Seller B attempts to update shipment for Order 3
    res = client.patch(
        "/api/seller/orders/ord-a-only-103/shipment",
        headers=seller_b_headers,
        json={"status": "DISPATCHED", "carrier_name": "DHL", "tracking_number": "TRK-HACK"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_order_state_gate_blocks_unpaid_order(client, seller_a_headers):
    # Order 2 is in PENDING_PAYMENT
    res = client.patch(
        "/api/seller/orders/ord-pending-102/shipment",
        headers=seller_a_headers,
        json={"carrier_name": "DHL", "tracking_number": "TRK-PENDING", "status": "DISPATCHED"},
    )
    assert res.status_code == 400
    assert "Order must be PAID" in res.json()["detail"]


def test_shipment_status_transition_validations(client, seller_a_headers):
    # 1. Reject transition to DISPATCHED if carrier_name or tracking_number is missing/empty
    res_empty_trk = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=seller_a_headers,
        json={"status": "DISPATCHED", "carrier_name": "DHL", "tracking_number": "   "},
    )
    assert res_empty_trk.status_code == 400
    assert "tracking_number cannot be empty" in res_empty_trk.json()["detail"]

    res_empty_carrier = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=seller_a_headers,
        json={"status": "DISPATCHED", "carrier_name": "  ", "tracking_number": "TRK-VALID"},
    )
    assert res_empty_carrier.status_code == 400
    assert "carrier_name cannot be empty" in res_empty_carrier.json()["detail"]

    # 2. Valid transition to DISPATCHED
    res_dispatch = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=seller_a_headers,
        json={"status": "DISPATCHED", "carrier_name": "DHL Express", "tracking_number": "TRK-DHL-101"},
    )
    assert res_dispatch.status_code == 200
    shp = res_dispatch.json()["shipment"]
    assert shp["status"] == "DISPATCHED"
    assert shp["carrier_name"] == "DHL Express"
    assert shp["tracking_number"] == "TRK-DHL-101"

    # 3. Valid transition to DELIVERED
    res_deliver = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=seller_a_headers,
        json={"status": "DELIVERED"},
    )
    assert res_deliver.status_code == 200
    assert res_deliver.json()["shipment"]["status"] == "DELIVERED"

    # 4. Reject modifying already DELIVERED shipment (terminal state)
    res_after_delivered = client.patch(
        "/api/seller/orders/ord-multi-101/shipment",
        headers=seller_a_headers,
        json={"status": "DISPATCHED"},
    )
    assert res_after_delivered.status_code == 400
    assert "already been DELIVERED" in res_after_delivered.json()["detail"]


def test_multi_seller_payment_simulation_creates_shipments_per_seller(client, session, buyer_headers):
    # Create fresh multi-seller order in PENDING_PAYMENT
    order_new = Order(
        id="ord-sim-multi-201",
        user_id="usr-buyer-1",
        status="PENDING_PAYMENT",
        total_amount=Decimal("250.00"),
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    oi_1 = OrderItem(
        id="oi-sim-1",
        order_id="ord-sim-multi-201",
        product_id="prod-a",
        stock_id="stk-a",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("100.00"),
    )
    oi_2 = OrderItem(
        id="oi-sim-2",
        order_id="ord-sim-multi-201",
        product_id="prod-b",
        stock_id="stk-b",
        variant_key="32",
        quantity=1,
        unit_price=Decimal("150.00"),
    )
    order_new.items.extend([oi_1, oi_2])
    session.add(order_new)
    session.commit()

    # Call simulate payment
    res = client.post(
        "/api/orders/ord-sim-multi-201/simulate-payment",
        headers=buyer_headers,
        json={"outcome": "SUCCESS"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    order_resp = data["order"]
    assert order_resp["status"] == "PAID"

    # Single dict shipment key contract preserved (6 keys)
    assert isinstance(order_resp["shipment"], dict)
    assert set(order_resp["shipment"].keys()) == {
        "id", "order_id", "carrier_name", "tracking_number",
        "status", "estimated_delivery"
    }

    # Supplementary shipments list contains 2 shipments (1 per seller)
    assert isinstance(order_resp["shipments"], list)
    assert len(order_resp["shipments"]) == 2

    # Verify both shipments in database have status PREPARING and tracking_number=None
    shipments_in_db = session.query(Shipment).filter_by(order_id="ord-sim-multi-201").all()
    assert len(shipments_in_db) == 2
    sellers_in_db = {s.seller_id for s in shipments_in_db}
    assert sellers_in_db == {"usr-seller-a", "usr-seller-b"}
    for s in shipments_in_db:
        assert s.status == "PREPARING"
        assert s.tracking_number is None

    # Idempotent call: simulating payment again should succeed without creating extra shipments
    res2 = client.post(
        "/api/orders/ord-sim-multi-201/simulate-payment",
        headers=buyer_headers,
        json={"outcome": "SUCCESS"},
    )
    assert res2.status_code == 200
    shipments_after = session.query(Shipment).filter_by(order_id="ord-sim-multi-201").all()
    assert len(shipments_after) == 2


def test_seller_with_no_orders_returns_empty_list(client, session):
    """A seller with no orders must receive 200 OK and an empty list [], not 500."""
    seller_c = User(
        id="usr-seller-c",
        email="seller_c@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        name="Seller C",
        store_name="Boutique C",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    session.add(seller_c)
    session.commit()

    token_c = create_access_token({"sub": "seller_c@fashion.com"})
    res = client.get("/api/seller/orders", headers={"Authorization": f"Bearer {token_c}"})
    assert res.status_code == 200
    assert res.json() == []


def test_seller_isolation_from_other_sellers(client, session, seller_b_headers):
    """Seller B only sees orders with Seller B's pieces; cannot see Seller A's exclusive orders."""
    res_b = client.get("/api/seller/orders", headers=seller_b_headers)
    assert res_b.status_code == 200
    order_ids = [o["id"] for o in res_b.json()]
    # ord-multi-101 has Seller B items -> must be visible
    assert "ord-multi-101" in order_ids
    # ord-pending-102 only has Seller A items -> must NOT be visible
    assert "ord-pending-102" not in order_ids


def test_seller_orders_excludes_cancelled_orders_and_preserves_active(client, session, seller_a_headers):
    """CANCELLED orders must not be returned in GET /api/seller/orders, while active/pending orders remain."""
    # Create a cancelled order with items belonging to Seller A
    order_cancelled = Order(
        id="ord-cancelled-seller-a",
        user_id="usr-buyer-1",
        status="CANCELLED",
        total_amount=Decimal("100.00"),
        created_at=BASE_TIME + timedelta(hours=1),
        updated_at=BASE_TIME + timedelta(hours=1),
    )
    order_cancelled.items.append(
        OrderItem(
            id="oi-cancelled-a",
            order_id="ord-cancelled-seller-a",
            product_id="prod-a",
            stock_id="stk-a",
            variant_key="M",
            quantity=1,
            unit_price=Decimal("100.00"),
        )
    )
    # Also add a shipment for this cancelled order to ensure it remains in DB
    shp_cancelled = Shipment(
        id="shp-cancelled-a",
        order_id="ord-cancelled-seller-a",
        seller_id="usr-seller-a",
        carrier_name="Standard Delivery",
        tracking_number="TRK-CANCELLED-1",
        status="PREPARING",
        created_at=BASE_TIME + timedelta(hours=1),
    )
    session.add_all([order_cancelled, shp_cancelled])
    session.commit()

    # Query seller orders
    res = client.get("/api/seller/orders", headers=seller_a_headers)
    assert res.status_code == 200
    orders = res.json()
    order_ids = [o["id"] for o in orders]

    # CANCELLED order must NOT appear
    assert "ord-cancelled-seller-a" not in order_ids

    # Active orders (ord-multi-101 which is PAID, and ord-pending-102 which is PENDING_PAYMENT) MUST appear
    assert "ord-multi-101" in order_ids
    assert "ord-pending-102" in order_ids

    # Confirm CANCELLED order and shipment are untouched in DB
    db_order = session.get(Order, "ord-cancelled-seller-a")
    assert db_order is not None
    assert db_order.status == "CANCELLED"
    db_shp = session.get(Shipment, "shp-cancelled-a")
    assert db_shp is not None
    assert db_shp.seller_id == "usr-seller-a"


def test_cancelling_pending_order_removes_it_from_seller_orders(client, session, seller_a_headers, buyer_headers):
    """When a buyer cancels an order, it must disappear from seller orders while remaining in buyer orders."""
    # Before cancel: ord-pending-102 is PENDING_PAYMENT -> visible to Seller A
    res_before = client.get("/api/seller/orders", headers=seller_a_headers)
    assert res_before.status_code == 200
    assert any(o["id"] == "ord-pending-102" for o in res_before.json())

    # Buyer cancels the order
    cancel_res = client.post("/api/orders/ord-pending-102/cancel", headers=buyer_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # After cancel: ord-pending-102 must NOT appear in Seller A's orders
    res_after = client.get("/api/seller/orders", headers=seller_a_headers)
    assert res_after.status_code == 200
    assert not any(o["id"] == "ord-pending-102" for o in res_after.json())

    # But buyer can still view their cancelled order details
    buyer_order_res = client.get("/api/orders/ord-pending-102", headers=buyer_headers)
    assert buyer_order_res.status_code == 200
    assert buyer_order_res.json()["status"] == "CANCELLED"


