"""Unit and integration tests for Single Account (Buyer + Seller) feature.

Validates:
1. Unified registration without role selector (defaults to 'buyer').
2. Backward compatibility for legacy role registrations.
3. 'Become a Seller' endpoint functionality and instant activation.
4. Validation and duplicate store name prevention.
5. Prevent existing sellers from creating duplicate stores.
6. Session and identity continuity (same user ID, email, and JWT).
7. Dual-role capabilities: seller can place orders, view in my-orders.
8. Tenant isolation: Seller A cannot inspect competitor Seller B's orders.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

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


@pytest.fixture
def test_db_session():
    """Create an isolated SQLite in-memory database and seed test accounts."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    # 1. Existing Seller A with a boutique and product
    seller_a = User(
        id="user-seller-a",
        email="seller_a@fashion.com",
        password_hash=hash_password("Password123!"),
        role="seller",
        name="Atelier Alpha",
        store_name="Alpha Boutique",
        created_at=now,
        updated_at=now,
    )
    # 2. Existing Seller B with a boutique and product
    seller_b = User(
        id="user-seller-b",
        email="seller_b@fashion.com",
        password_hash=hash_password("Password123!"),
        role="seller",
        name="Atelier Beta",
        store_name="Beta Boutique",
        created_at=now,
        updated_at=now,
    )
    # 3. Standard Buyer
    buyer = User(
        id="user-buyer-1",
        email="buyer@fashion.com",
        password_hash=hash_password("Password123!"),
        role="buyer",
        name="Emma Stone",
        store_name=None,
        created_at=now,
        updated_at=now,
    )
    session.add_all([seller_a, seller_b, buyer])

    # Products for Seller A and B
    prod_a = Product(
        id="prod-a-01",
        name="Alpha Silk Shirt",
        description="Silk shirt by Alpha",
        price=Decimal("120.00"),
        stock_quantity=10,
        category="Shirts",
        seller_id=seller_a.id,
        is_active=True,
    )
    prod_b = Product(
        id="prod-b-01",
        name="Beta Wool Coat",
        description="Wool coat by Beta",
        price=Decimal("250.00"),
        stock_quantity=5,
        category="Jackets",
        seller_id=seller_b.id,
        is_active=True,
    )
    session.add_all([prod_a, prod_b])

    stock_a = Stock(
        id="stock-a-01",
        product_id=prod_a.id,
        variant_key="M",
        available_quantity=10,
        updated_at=now,
    )
    stock_b = Stock(
        id="stock-b-01",
        product_id=prod_b.id,
        variant_key="L",
        available_quantity=5,
        updated_at=now,
    )
    session.add_all([stock_a, stock_b])

    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def buyer_token():
    return create_access_token({"sub": "buyer@fashion.com"})


@pytest.fixture
def seller_a_token():
    return create_access_token({"sub": "seller_a@fashion.com"})


@pytest.fixture
def seller_b_token():
    return create_access_token({"sub": "seller_b@fashion.com"})


# -------------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------------

def test_unified_register_without_role(client):
    """1. Single account registration without role defaults to 'buyer'."""
    res = client.post(
        "/api/auth/register",
        json={
            "email": "new_unified_buyer@fashion.com",
            "password": "SecurePassword123!",
            "name": "Jane Shopper",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "new_unified_buyer@fashion.com"
    assert data["role"] == "buyer"
    assert data["name"] == "Jane Shopper"
    assert data["store_name"] is None


def test_register_buyer_with_store_name_fails(client):
    """2. Buyer cannot register with a store name."""
    res = client.post(
        "/api/auth/register",
        json={
            "email": "invalid_buyer@fashion.com",
            "password": "SecurePassword123!",
            "role": "buyer",
            "store_name": "Invalid Atelier",
        },
    )
    assert res.status_code == 400
    assert "Buyers cannot have a store name" in res.json()["detail"]


def test_register_backward_compatibility(client):
    """3. Backward compatibility: existing clients can still supply role."""
    # Legacy buyer registration
    res1 = client.post(
        "/api/auth/register",
        json={
            "email": "legacy_buyer@fashion.com",
            "password": "SecurePassword123!",
            "role": "buyer",
        },
    )
    assert res1.status_code == 200
    assert res1.json()["role"] == "buyer"

    # Legacy seller registration
    res2 = client.post(
        "/api/auth/register",
        json={
            "email": "legacy_seller@fashion.com",
            "password": "SecurePassword123!",
            "role": "seller",
            "store_name": "Legacy Atelier",
        },
    )
    assert res2.status_code == 200
    assert res2.json()["role"] == "seller"
    assert res2.json()["store_name"] == "Legacy Atelier"


def test_become_seller_requires_auth(client):
    """4. POST /api/seller/become-seller requires a valid JWT token."""
    res = client.post("/api/seller/become-seller", json={"store_name": "Maison Noir"})
    assert res.status_code in [401, 403]


def test_become_seller_validation(client, buyer_token):
    """5. POST /api/seller/become-seller validates store name length."""
    headers = {"Authorization": f"Bearer {buyer_token}"}

    # Empty store name
    res1 = client.post("/api/seller/become-seller", json={"store_name": ""}, headers=headers)
    assert res1.status_code in [400, 422]

    # Too short (< 2 characters)
    res2 = client.post("/api/seller/become-seller", json={"store_name": "X"}, headers=headers)
    assert res2.status_code in [400, 422]


def test_become_seller_success_instant_activation(client, buyer_token, test_db_session):
    """6. Buyer successfully becomes a seller with instant ACTIVE status."""
    headers = {"Authorization": f"Bearer {buyer_token}"}

    res = client.post(
        "/api/seller/become-seller",
        json={"store_name": "Maison Laurent"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "seller"
    assert data["store_name"] == "Maison Laurent"
    assert data["id"] == "user-buyer-1"
    assert data["email"] == "buyer@fashion.com"

    # Verify session continuity via /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["role"] == "seller"
    assert me_data["store_name"] == "Maison Laurent"


def test_become_seller_duplicate_store_prevention(client, buyer_token):
    """7. Prevent duplicate store creation if user is already a seller."""
    headers = {"Authorization": f"Bearer {buyer_token}"}

    # First activation succeeds
    res1 = client.post(
        "/api/seller/become-seller",
        json={"store_name": "Maison Elegance"},
        headers=headers,
    )
    assert res1.status_code == 200

    # Second attempt on same account fails
    res2 = client.post(
        "/api/seller/become-seller",
        json={"store_name": "Maison Two"},
        headers=headers,
    )
    assert res2.status_code == 400
    assert "already a registered seller" in res2.json()["detail"]


def test_become_seller_duplicate_name_case_insensitive(client, buyer_token):
    """8. Prevent claiming an existing store name (case-insensitive check)."""
    headers = {"Authorization": f"Bearer {buyer_token}"}

    # Attempt to take existing Seller A's store name with different casing
    res = client.post(
        "/api/seller/become-seller",
        json={"store_name": "alpha boutique"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "already taken" in res.json()["detail"].lower()


def test_seller_can_purchase_and_view_own_orders(client, seller_a_token):
    """9. Dual role: Seller A can purchase Seller B's product and view it in my-orders."""
    headers = {"Authorization": f"Bearer {seller_a_token}"}

    # Seller A places order for Seller B's product
    order_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-b-01", "variant_key": "L", "quantity": 1}]},
        headers=headers,
    )
    assert order_res.status_code == 200
    order_id = order_res.json()["id"]

    # Seller A views my-orders
    my_orders_res = client.get("/api/orders/my-orders", headers=headers)
    assert my_orders_res.status_code == 200
    order_ids = [o["id"] for o in my_orders_res.json()]
    assert order_id in order_ids

    # Seller A can view this specific order
    detail_res = client.get(f"/api/orders/{order_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == order_id


def test_seller_tenant_isolation_on_order_details(client, buyer_token, seller_a_token, seller_b_token):
    """10. Tenant isolation: Seller A cannot view an order created by Buyer that only contains Seller B's products."""
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    seller_a_headers = {"Authorization": f"Bearer {seller_a_token}"}
    seller_b_headers = {"Authorization": f"Bearer {seller_b_token}"}

    # Buyer purchases Seller B's product
    order_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-b-01", "variant_key": "L", "quantity": 1}]},
        headers=buyer_headers,
    )
    assert order_res.status_code == 200
    order_id = order_res.json()["id"]

    # Buyer can view own order
    res_buyer = client.get(f"/api/orders/{order_id}", headers=buyer_headers)
    assert res_buyer.status_code == 200

    # Seller B (the selling party) can view this order
    res_seller_b = client.get(f"/api/orders/{order_id}", headers=seller_b_headers)
    assert res_seller_b.status_code == 200

    # Seller A (unrelated third-party competitor) is forbidden from viewing this order
    res_seller_a = client.get(f"/api/orders/{order_id}", headers=seller_a_headers)
    assert res_seller_a.status_code == 403
    assert "You do not have permission to view this order" in res_seller_a.json()["detail"]


def test_multi_seller_order_isolation_and_shipment_privacy(
    client, test_db_session, buyer_token, seller_a_token, seller_b_token
):
    """11. Multi-seller order isolation and privacy:
    - Buyer purchases items from both Seller A and Seller B.
    - Buyer sees all items and all shipments.
    - Seller A sees only Seller A's items and shipment.
    - Seller B sees only Seller B's items and shipment.
    - Unrelated Seller C is rejected (403).
    - Unauthenticated caller is rejected (401).
    - Filtered response strictly conforms to OrderResponse schema (does not break frontend).
    """
    now = datetime.now(timezone.utc)
    # Register Seller C who has no items in the order
    seller_c = User(
        id="user-seller-c",
        email="seller_c@fashion.com",
        password_hash=hash_password("Password123!"),
        role="seller",
        name="Atelier Gamma",
        store_name="Gamma Boutique",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(seller_c)
    test_db_session.commit()
    seller_c_token = create_access_token({"sub": "seller_c@fashion.com"})

    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    seller_a_headers = {"Authorization": f"Bearer {seller_a_token}"}
    seller_b_headers = {"Authorization": f"Bearer {seller_b_token}"}
    seller_c_headers = {"Authorization": f"Bearer {seller_c_token}"}

    # 1. Buyer creates multi-seller order: 1 item from Seller A ($120.00) + 1 item from Seller B ($250.00)
    order_res = client.post(
        "/api/orders/create",
        json={
            "items": [
                {"product_id": "prod-a-01", "variant_key": "M", "quantity": 1},
                {"product_id": "prod-b-01", "variant_key": "L", "quantity": 1},
            ]
        },
        headers=buyer_headers,
    )
    assert order_res.status_code == 200
    order_id = order_res.json()["id"]

    # 2. Simulate payment so shipments are created for both sellers
    pay_res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS", "payment_method": "SIMULATED_CARD"},
        headers=buyer_headers,
    )
    assert pay_res.status_code == 200

    # 3. Seller A and Seller B update their shipments with distinct tracking numbers
    shp_a_res = client.patch(
        f"/api/seller/orders/{order_id}/shipment",
        json={"tracking_number": "TRK-ALPHA-9999", "carrier_name": "Alpha Express"},
        headers=seller_a_headers,
    )
    assert shp_a_res.status_code == 200

    shp_b_res = client.patch(
        f"/api/seller/orders/{order_id}/shipment",
        json={"tracking_number": "TRK-BETA-8888", "carrier_name": "Beta Courier"},
        headers=seller_b_headers,
    )
    assert shp_b_res.status_code == 200

    # 4. Check Buyer View: Buyer must see all items, all shipments, and full total
    res_buyer = client.get(f"/api/orders/{order_id}", headers=buyer_headers)
    assert res_buyer.status_code == 200
    buyer_data = res_buyer.json()
    assert len(buyer_data["items"]) == 2
    item_prods = {it["product_id"] for it in buyer_data["items"]}
    assert item_prods == {"prod-a-01", "prod-b-01"}
    assert buyer_data["total_amount"] == 370.0
    assert len(buyer_data["shipments"]) == 2
    tracking_numbers = {s["tracking_number"] for s in buyer_data["shipments"]}
    assert tracking_numbers == {"TRK-ALPHA-9999", "TRK-BETA-8888"}

    # 5. Check Seller A View: Seller A must see ONLY Seller A's items and shipment
    res_seller_a = client.get(f"/api/orders/{order_id}", headers=seller_a_headers)
    assert res_seller_a.status_code == 200
    seller_a_data = res_seller_a.json()
    assert len(seller_a_data["items"]) == 1
    assert seller_a_data["items"][0]["product_id"] == "prod-a-01"
    assert seller_a_data["items"][0]["unit_price"] == 120.0
    assert seller_a_data["total_amount"] == 120.0
    # Competitor items must NOT be present
    assert not any(it["product_id"] == "prod-b-01" for it in seller_a_data["items"])
    # Competitor shipments and tracking must NOT be leaked
    assert len(seller_a_data["shipments"]) == 1
    assert seller_a_data["shipments"][0]["tracking_number"] == "TRK-ALPHA-9999"
    assert seller_a_data["shipment"]["tracking_number"] == "TRK-ALPHA-9999"
    assert "TRK-BETA-8888" not in str(seller_a_data)

    # 6. Check Seller B View: Seller B must see ONLY Seller B's items and shipment
    res_seller_b = client.get(f"/api/orders/{order_id}", headers=seller_b_headers)
    assert res_seller_b.status_code == 200
    seller_b_data = res_seller_b.json()
    assert len(seller_b_data["items"]) == 1
    assert seller_b_data["items"][0]["product_id"] == "prod-b-01"
    assert seller_b_data["items"][0]["unit_price"] == 250.0
    assert seller_b_data["total_amount"] == 250.0
    # Competitor items must NOT be present
    assert not any(it["product_id"] == "prod-a-01" for it in seller_b_data["items"])
    # Competitor shipments and tracking must NOT be leaked
    assert len(seller_b_data["shipments"]) == 1
    assert seller_b_data["shipments"][0]["tracking_number"] == "TRK-BETA-8888"
    assert seller_b_data["shipment"]["tracking_number"] == "TRK-BETA-8888"
    assert "TRK-ALPHA-9999" not in str(seller_b_data)

    # 7. Check Seller C View: Unrelated seller has no items in the order -> 403 Forbidden
    res_seller_c = client.get(f"/api/orders/{order_id}", headers=seller_c_headers)
    assert res_seller_c.status_code == 403
    assert "You do not have permission to view this order" in res_seller_c.json()["detail"]

    # 8. Unauthenticated caller -> 401 Unauthorized
    res_anon = client.get(f"/api/orders/{order_id}")
    assert res_anon.status_code == 401

    # 9. Response schema validation: conforms cleanly to OrderResponse Pydantic model
    from app.schemas import OrderResponse
    buyer_model = OrderResponse.model_validate(buyer_data)
    seller_a_model = OrderResponse.model_validate(seller_a_data)
    seller_b_model = OrderResponse.model_validate(seller_b_data)
    assert buyer_model.id == order_id
    assert seller_a_model.id == order_id
    assert seller_b_model.id == order_id


def test_become_seller_race_condition_and_integrity_error(client, test_db_session):
    """12. Race condition protection: IntegrityError on commit is caught and rolled back, returning 400."""
    from unittest.mock import patch
    from sqlalchemy.exc import IntegrityError

    now = datetime.now(timezone.utc)
    buyer2 = User(
        id="user-buyer-2",
        email="buyer2@fashion.com",
        password_hash=hash_password("Password123!"),
        role="buyer",
        name="Bob Smith",
        store_name=None,
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer2)
    test_db_session.commit()
    buyer2_token = create_access_token({"sub": "buyer2@fashion.com"})
    headers = {"Authorization": f"Bearer {buyer2_token}"}

    # Simulate race condition where db.commit() raises IntegrityError
    with patch.object(test_db_session, "commit", side_effect=IntegrityError("uq_users_store_name_lower", {}, Exception("unique constraint failed"))):
        res = client.post(
            "/api/seller/become-seller",
            json={"store_name": "Concurrent Store"},
            headers=headers,
        )
        assert res.status_code == 400
        assert "Store name already taken" in res.json()["detail"]

    # Verify user remains buyer with no store_name after rollback
    test_db_session.refresh(buyer2)
    assert buyer2.role == "buyer"
    assert buyer2.store_name is None

    # Verify database level unique constraint raises IntegrityError on case-insensitive duplicate
    user_dup = User(
        id="user-dup-store",
        email="dup@fashion.com",
        password_hash=hash_password("Password123!"),
        role="seller",
        name="Dup Seller",
        store_name="alpha boutique",  # Same as 'Alpha Boutique'
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(user_dup)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

