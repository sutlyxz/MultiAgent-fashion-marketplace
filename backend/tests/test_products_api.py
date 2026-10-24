"""Integration tests for Public Products API connected to PostgreSQL / SQLAlchemy.

All tests use FastAPI TestClient and an isolated SQLite in-memory database
by overriding the `get_db` dependency. No live or dev database is touched.
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

from app.db_connection import Base, get_db
from app.main import app
from app.models import Order, OrderItem, Product, Stock, User


@pytest.fixture
def test_db_session():
    """Create an isolated SQLite in-memory database and populate test data."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)
    # 1. Seed Seller User
    seller = User(
        id="seller-100",
        email="test_seller@fashion.com",
        password_hash="hashed_pw",
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add(seller)
    session.flush()

    # 2. Seed Products
    p1 = Product(
        id="prod-100",
        name="Leather Biker Jacket",
        description="Premium black leather jacket.",
        price=Decimal("199.99"),
        stock_quantity=15,
        category="Jackets",
        seller_id="seller-100",
        is_active=True,
    )
    p2 = Product(
        id="prod-200",
        name="Floral Summer Blouse",
        description="Lightweight floral print shirt.",
        price=Decimal("45.50"),
        stock_quantity=20,
        category="Shirts",
        seller_id="seller-100",
        is_active=True,
    )
    p3 = Product(
        id="prod-150",
        name="Denim Jacket",
        description="Classic denim jacket.",
        price=Decimal("89.99"),
        stock_quantity=10,
        category="Jackets",
        seller_id="seller-100",
        is_active=True,
    )
    p_inactive = Product(
        id="prod-300",
        name="Hidden Inactive Shirt",
        description="Not visible to public.",
        price=Decimal("29.00"),
        stock_quantity=5,
        category="Shirts",
        seller_id="seller-100",
        is_active=False,
    )
    session.add_all([p1, p2, p3, p_inactive])
    session.flush()

    # 3. Seed Stock Variants
    s1_m = Stock(
        id="stk-101",
        product_id="prod-100",
        variant_key="M",
        available_quantity=5,
        updated_at=now,
    )
    s1_l = Stock(
        id="stk-102",
        product_id="prod-100",
        variant_key="L",
        available_quantity=10,
        updated_at=now,
    )
    s2_s = Stock(
        id="stk-201",
        product_id="prod-200",
        variant_key="S",
        available_quantity=20,
        updated_at=now,
    )
    s3_m = Stock(
        id="stk-151",
        product_id="prod-150",
        variant_key="M",
        available_quantity=10,
        updated_at=now,
    )
    session.add_all([s1_m, s1_l, s2_s, s3_m])
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


def test_list_products_from_database(client):
    """GET /api/products returns active products from database."""
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()

    # Inactive product (prod-300) must be excluded
    assert len(data) == 3
    prod_ids = {p["id"] for p in data}
    assert prod_ids == {"prod-100", "prod-150", "prod-200"}

    # Verify variants embedded
    p1_data = next(p for p in data if p["id"] == "prod-100")
    assert len(p1_data["variants"]) == 2
    assert {v["variant_key"] for v in p1_data["variants"]} == {"M", "L"}


def test_list_products_search_filter(client):
    """GET /api/products?search=... performs case-insensitive name/description search."""
    res = client.get("/api/products?search=LEATHER")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "prod-100"

    res = client.get("/api/products?search=print")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "prod-200"

    res = client.get("/api/products?search=nonexistentterm")
    assert res.status_code == 200
    assert res.json() == []


def test_list_products_sort_by_price_asc(client):
    """GET /api/products?sort_by=price&sort_order=asc sorts products lowest price first."""
    res = client.get("/api/products?sort_by=price&sort_order=asc")
    assert res.status_code == 200
    data = res.json()
    prices = [p["price"] for p in data]
    assert prices == sorted(prices)
    assert data[0]["id"] == "prod-200"  # 45.50
    assert data[1]["id"] == "prod-150"  # 89.99
    assert data[2]["id"] == "prod-100"  # 199.99


def test_list_products_sort_by_price_desc(client):
    """GET /api/products?sort_by=price&sort_order=desc sorts products highest price first."""
    res = client.get("/api/products?sort_by=price&sort_order=desc")
    assert res.status_code == 200
    data = res.json()
    prices = [p["price"] for p in data]
    assert prices == sorted(prices, reverse=True)
    assert data[0]["id"] == "prod-100"  # 199.99
    assert data[1]["id"] == "prod-150"  # 89.99
    assert data[2]["id"] == "prod-200"  # 45.50


def test_list_products_sort_with_active_search(client):
    """GET /api/products with search and price sorting maintains search query filtering."""
    res = client.get("/api/products?search=Jacket&sort_by=price&sort_order=asc")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["id"] == "prod-150"  # 89.99
    assert data[1]["id"] == "prod-100"  # 199.99

    res_desc = client.get("/api/products?search=Jacket&sort_by=price&sort_order=desc")
    assert res_desc.status_code == 200
    data_desc = res_desc.json()
    assert len(data_desc) == 2
    assert data_desc[0]["id"] == "prod-100"  # 199.99
    assert data_desc[1]["id"] == "prod-150"  # 89.99


def test_list_products_category_and_price_filters(client):
    """GET /api/products filters by category and price range correctly."""
    res = client.get("/api/products?category=Jackets&min_price=100.00")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "prod-100"

    res_max = client.get("/api/products?max_price=100.00&sort_by=price&sort_order=asc")
    assert res_max.status_code == 200
    data_max = res_max.json()
    assert len(data_max) == 2
    assert data_max[0]["id"] == "prod-200"  # 45.50
    assert data_max[1]["id"] == "prod-150"  # 89.99


def test_get_product_by_id_success(client):
    """GET /api/products/{id} returns product details with variants."""
    res = client.get("/api/products/prod-100")
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == "prod-100"
    assert data["name"] == "Leather Biker Jacket"
    assert data["price"] == 199.99
    assert isinstance(data["price"], float)
    assert data["stock_quantity"] == 15
    assert len(data["variants"]) == 2


def test_get_product_by_id_not_found(client):
    """GET /api/products/{id} with missing ID returns 404."""
    res = client.get("/api/products/missing-prod-999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Product not found"}


def test_check_stock_sufficient(client):
    """GET /api/products/check-stock with requested quantity <= available stock."""
    res = client.get("/api/products/check-stock?product_id=prod-100&variant_key=M&quantity=3")
    assert res.status_code == 200
    data = res.json()

    assert data["product_id"] == "prod-100"
    assert data["variant_key"] == "M"
    assert data["requested_quantity"] == 3
    assert data["available_quantity"] == 5
    assert data["is_fulfillable"] is True


def test_check_stock_insufficient(client):
    """GET /api/products/check-stock with requested quantity > available stock."""
    res = client.get("/api/products/check-stock?product_id=prod-100&variant_key=M&quantity=10")
    assert res.status_code == 200
    data = res.json()

    assert data["requested_quantity"] == 10
    assert data["available_quantity"] == 5
    assert data["is_fulfillable"] is False


def test_check_stock_invalid_inputs(client):
    """GET /api/products/check-stock handles missing variant and non-positive quantity."""
    res = client.get("/api/products/check-stock?product_id=prod-100&variant_key=M&quantity=0")
    assert res.status_code == 400
    assert res.json() == {"detail": "Quantity must be a positive integer"}

    res = client.get("/api/products/check-stock?product_id=prod-100&variant_key=XXL&quantity=1")
    assert res.status_code == 404
    assert res.json() == {"detail": "Product variant not found"}


def test_product_types_and_schema_correctness(client):
    """Verify price is float, stock_quantity is int, and types match schema."""
    res = client.get("/api/products/prod-200")
    assert res.status_code == 200
    data = res.json()

    assert type(data["price"]) is float
    assert data["price"] == 45.50
    assert type(data["stock_quantity"]) is int
    assert data["stock_quantity"] == 20


def test_read_only_stock_not_modified(client, test_db_session):
    """Calling product listing and stock check APIs does not alter DB stock levels."""
    client.get("/api/products")
    client.get("/api/products/prod-100")
    client.get("/api/products/check-stock?product_id=prod-100&variant_key=M&quantity=3")

    stk = test_db_session.get(Stock, "stk-101")
    assert stk.available_quantity == 5


def test_api_does_not_depend_on_in_memory_db(client, monkeypatch):
    """Products API returns database content even if in-memory db.products is cleared."""
    from app.database import db

    monkeypatch.setattr(db, "products", [])
    monkeypatch.setattr(db, "stocks", [])

    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3


def test_product_response_includes_media_and_color_fields(client):
    """Product responses must include image_url and color fields."""
    res = client.get("/api/products/prod-100")
    assert res.status_code == 200
    data = res.json()
    assert "image_url" in data
    assert "color" in data
    assert data["image_url"] is None
    assert data["color"] is None


def test_list_products_filter_by_color(client, test_db_session):
    """GET /api/products?color=... filters by garment color."""
    p1 = test_db_session.get(Product, "prod-100")
    p1.color = "Black"
    p2 = test_db_session.get(Product, "prod-150")
    p2.color = "Indigo"
    test_db_session.commit()

    res = client.get("/api/products?color=black")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "prod-100"
    assert data[0]["color"] == "Black"

    res_indigo = client.get("/api/products?color=INDIGO")
    assert res_indigo.status_code == 200
    data_indigo = res_indigo.json()
    assert len(data_indigo) == 1
    assert data_indigo[0]["id"] == "prod-150"


def test_create_product_by_seller_with_media_and_color(client, test_db_session):
    """Authenticated seller can create a product with image_url and color."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Wool Trench Coat",
        "description": "Double-breasted tailored trench coat.",
        "price": 289.00,
        "stock_quantity": 8,
        "category": "Coats",
        "image_url": "https://images.example.com/trench.jpg",
        "color": "Camel",
    }
    res = client.post("/api/products", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Wool Trench Coat"
    assert data["seller_id"] == "seller-100"
    assert data["image_url"] == "https://images.example.com/trench.jpg"
    assert data["color"] == "Camel"

    # Confirm in DB
    db_prod = test_db_session.get(Product, data["id"])
    assert db_prod is not None
    assert db_prod.seller_id == "seller-100"
    assert db_prod.image_url == "https://images.example.com/trench.jpg"
    assert db_prod.color == "Camel"


def test_create_product_forbidden_for_buyer(client, test_db_session):
    """Buyers cannot create products (403 Forbidden)."""
    from app.auth import create_access_token, hash_password

    now = datetime.now(timezone.utc)
    buyer = User(
        id="buyer-sub",
        email="shopper@fashion.com",
        password_hash=hash_password("Pass123"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.commit()

    token = create_access_token({"sub": "shopper@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Unauthorized Coat",
        "description": "desc",
        "price": 50.00,
        "category": "Coats",
    }
    res = client.post("/api/products", headers=headers, json=payload)
    assert res.status_code == 403
    assert res.json() == {"detail": "Only sellers are authorized to perform this action"}


def test_update_product_by_owning_seller(client, test_db_session):
    """Owning seller can update product fields including image_url and color."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "image_url": "https://images.example.com/updated_biker.jpg",
        "color": "Midnight Black",
        "price": 219.99,
    }
    res = client.patch("/api/products/prod-100", headers=headers, json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["image_url"] == "https://images.example.com/updated_biker.jpg"
    assert data["color"] == "Midnight Black"
    assert data["price"] == 219.99


def test_update_product_forbidden_for_other_seller(client, test_db_session):
    """A different seller cannot update another seller's product (403 Forbidden)."""
    from app.auth import create_access_token, hash_password

    now = datetime.now(timezone.utc)
    other_seller = User(
        id="seller-999",
        email="competitor@fashion.com",
        password_hash=hash_password("Pass123"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(other_seller)
    test_db_session.commit()

    token = create_access_token({"sub": "competitor@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={"name": "Hijacked Name"},
    )
    assert res.status_code == 403
    assert res.json() == {"detail": "You do not have permission to modify this product"}


def test_create_product_accepts_null_media_and_color(client):
    """Product creation accepts None / empty image_url and color."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Basic Tee",
        "description": "Essential tee.",
        "price": 25.00,
        "category": "Shirts",
        "image_url": None,
        "color": None,
    }
    res = client.post("/api/products", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["image_url"] is None
    assert data["color"] is None


def test_create_product_missing_or_invalid_token(client):
    """POST /api/products requires a valid seller Bearer token."""
    payload = {
        "name": "Ghost Item",
        "description": "desc",
        "price": 10.0,
        "category": "Shirts",
    }
    # 1. Missing token
    res_no_auth = client.post("/api/products", json=payload)
    assert res_no_auth.status_code == 401

    # 2. Invalid token
    res_bad_auth = client.post(
        "/api/products",
        headers={"Authorization": "Bearer badtoken123"},
        json=payload,
    )
    assert res_bad_auth.status_code == 401


def test_update_product_missing_or_invalid_token(client):
    """PATCH /api/products/{id} requires a valid seller Bearer token."""
    # 1. Missing token
    res_no_auth = client.patch("/api/products/prod-100", json={"price": 100.0})
    assert res_no_auth.status_code == 401

    # 2. Invalid token
    res_bad_auth = client.patch(
        "/api/products/prod-100",
        headers={"Authorization": "Bearer invalidtoken"},
        json={"price": 100.0},
    )
    assert res_bad_auth.status_code == 401


def test_update_product_not_found(client):
    """Updating a non-existent product returns 404."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(
        "/api/products/non-existent-product-id",
        headers=headers,
        json={"name": "New Name"},
    )
    assert res.status_code == 404
    assert res.json() == {"detail": "Product not found"}


def test_create_product_invalid_price_or_stock(client):
    """Product creation validates that price > 0 and stock_quantity >= 0."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Negative price
    res_neg_price = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "Invalid Price Item",
            "description": "desc",
            "price": -10.0,
            "category": "Shirts",
        },
    )
    assert res_neg_price.status_code == 422

    # Negative stock
    res_neg_stock = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "Invalid Stock Item",
            "description": "desc",
            "price": 10.0,
            "stock_quantity": -5,
            "category": "Shirts",
        },
    )
    assert res_neg_stock.status_code == 422


def test_list_seller_products_returns_own_products_including_inactive(client, test_db_session):
    """Seller can list all of their own products (including inactive), but not others' products."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/products/seller/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    # test_seller owns prod-100, prod-200, prod-150, and prod-300 (which is inactive)
    assert len(data) == 4
    ids = [item["id"] for item in data]
    assert "prod-100" in ids
    assert "prod-200" in ids
    assert "prod-150" in ids
    assert "prod-300" in ids  # Inactive product is present!
    inactive_prod = next(item for item in data if item["id"] == "prod-300")
    assert inactive_prod["is_active"] is False


def test_list_seller_products_forbidden_for_buyer(client, test_db_session):
    """Buyer cannot access GET /api/products/seller/me (403 Forbidden)."""
    from app.auth import create_access_token, hash_password

    now = datetime.now(timezone.utc)
    buyer = User(
        id="buyer-me-sub",
        email="shopper_me@fashion.com",
        password_hash=hash_password("Pass123"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.commit()

    token = create_access_token({"sub": "shopper_me@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/products/seller/me", headers=headers)
    assert res.status_code == 403
    assert res.json() == {"detail": "Only sellers are authorized to perform this action"}


def test_list_seller_products_unauthorized_without_token(client):
    """Accessing GET /api/products/seller/me without token returns 401."""
    res = client.get("/api/products/seller/me")
    assert res.status_code == 401


def test_create_product_with_variants(client, test_db_session):
    """Seller can create a product with stock variants, and total stock is synchronized."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Linen Wrap Blazer",
        "description": "Tailored summer blazer.",
        "price": 145.0,
        "category": "Jackets",
        "color": "Oatmeal",
        "image_url": "https://images.example.com/blazer.jpg",
        "variants": [
            {"variant_key": "S", "available_quantity": 8},
            {"variant_key": "M", "available_quantity": 12},
            {"variant_key": "L", "available_quantity": 4},
        ],
    }

    res = client.post("/api/products", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Linen Wrap Blazer"
    assert data["stock_quantity"] == 24  # 8 + 12 + 4
    assert len(data["variants"]) == 3
    keys = {v["variant_key"]: v["available_quantity"] for v in data["variants"]}
    assert keys == {"S": 8, "M": 12, "L": 4}


def test_create_product_duplicate_variants_rejected(client):
    """Creating a product with duplicate variant keys returns 400 Bad Request."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Duplicate Variant Top",
        "description": "desc",
        "price": 50.0,
        "category": "Tops",
        "variants": [
            {"variant_key": "M", "available_quantity": 5},
            {"variant_key": "m", "available_quantity": 10},
        ],
    }
    res = client.post("/api/products", headers=headers, json=payload)
    assert res.status_code == 400
    assert res.json() == {"detail": "Variant keys must be unique"}


def test_update_product_variants_and_status(client, test_db_session):
    """Seller can update product variants and toggle is_active status."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update prod-100 with new variants and deactivate
    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "is_active": False,
            "variants": [
                {"variant_key": "M", "available_quantity": 2},
                {"variant_key": "XL", "available_quantity": 7},
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_active"] is False
    assert data["stock_quantity"] == 9  # 2 + 7
    assert len(data["variants"]) == 2
    keys = {v["variant_key"]: v["available_quantity"] for v in data["variants"]}
    assert keys == {"M": 2, "XL": 7}

    # 2. Reactivate prod-100
    res_reactivate = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={"is_active": True},
    )
    assert res_reactivate.status_code == 200
    assert res_reactivate.json()["is_active"] is True


def test_update_product_preserves_stock_id_when_referenced_by_order(client, test_db_session):
    """Updating variant stock quantity preserves existing Stock.id when referenced by an order."""
    from app.auth import create_access_token

    # 1. Seed buyer and order referencing stk-101 (prod-100, variant M)
    now = datetime.now(timezone.utc)
    buyer = User(
        id="buyer-501",
        email="buyer501@example.com",
        password_hash="hashed_pw",
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.flush()

    order = Order(
        id="order-501",
        user_id="buyer-501",
        status="PENDING_PAYMENT",
        total_amount=Decimal("199.99"),
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(order)
    test_db_session.flush()

    order_item = OrderItem(
        id="item-501",
        order_id="order-501",
        product_id="prod-100",
        stock_id="stk-101",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("199.99"),
    )
    test_db_session.add(order_item)
    test_db_session.commit()

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Update prod-100 variants: change M quantity and keep L
    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "variants": [
                {"variant_key": "M", "available_quantity": 8},
                {"variant_key": "L", "available_quantity": 10},
            ]
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["stock_quantity"] == 18

    # Verify Stock.id for 'M' is STILL stk-101
    variant_m = next(v for v in data["variants"] if v["variant_key"] == "M")
    assert variant_m["id"] == "stk-101"
    assert variant_m["available_quantity"] == 8

    # Verify Order and OrderItem in database remain intact and reference stk-101
    db_item = test_db_session.get(OrderItem, "item-501")
    assert db_item is not None
    assert db_item.stock_id == "stk-101"
    assert db_item.quantity == 1


def test_update_product_can_add_new_size_and_delete_unreferenced_size(client, test_db_session):
    """Seller can add a new size and delete an unreferenced size."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # prod-100 initially has M (stk-101) and L (stk-102), neither has order items
    # Remove L, keep M, and add XS
    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "variants": [
                {"variant_key": "M", "available_quantity": 5},
                {"variant_key": "XS", "available_quantity": 3},
            ]
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["stock_quantity"] == 8  # 5 + 3
    variant_keys = {v["variant_key"] for v in data["variants"]}
    assert variant_keys == {"M", "XS"}

    # Verify L is deleted from database
    stk_l = test_db_session.get(Stock, "stk-102")
    assert stk_l is None


def test_update_product_rejects_deleting_referenced_variant_with_409(client, test_db_session):
    """Attempting to remove a variant referenced by an existing order returns 409 Conflict."""
    from app.auth import create_access_token

    # Seed buyer and order referencing stk-101 (M)
    now = datetime.now(timezone.utc)
    buyer = User(
        id="buyer-601",
        email="buyer601@example.com",
        password_hash="hashed_pw",
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.flush()

    order = Order(
        id="order-601",
        user_id="buyer-601",
        status="PENDING_PAYMENT",
        total_amount=Decimal("199.99"),
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(order)
    test_db_session.flush()

    order_item = OrderItem(
        id="item-601",
        order_id="order-601",
        product_id="prod-100",
        stock_id="stk-101",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("199.99"),
    )
    test_db_session.add(order_item)
    test_db_session.commit()

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to remove 'M' (only providing 'L')
    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "variants": [
                {"variant_key": "L", "available_quantity": 10},
            ]
        },
    )
    assert res.status_code == 409
    assert "referenced by existing orders" in res.json()["detail"]
    assert "'M'" in res.json()["detail"]

    # Verify stock stk-101 and order item item-601 still exist unchanged
    stk_m = test_db_session.get(Stock, "stk-101")
    assert stk_m is not None
    db_item = test_db_session.get(OrderItem, "item-601")
    assert db_item is not None


def test_update_product_rejects_duplicate_or_invalid_variants(client):
    """Updating product with duplicate variant keys or empty keys returns 400."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate variant keys
    res_dup = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "variants": [
                {"variant_key": "S", "available_quantity": 2},
                {"variant_key": "s", "available_quantity": 4},
            ]
        },
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["detail"] == "Variant keys must be unique"

    # Empty variant key
    res_empty = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "variants": [
                {"variant_key": "   ", "available_quantity": 2},
            ]
        },
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()


def test_update_product_rolls_back_on_error(client, test_db_session):
    """If an update fails (e.g. 409 Conflict), all modifications roll back."""
    from app.auth import create_access_token

    # Seed buyer and order referencing stk-101 (M)
    now = datetime.now(timezone.utc)
    buyer = User(
        id="buyer-701",
        email="buyer701@example.com",
        password_hash="hashed_pw",
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.flush()

    order = Order(
        id="order-701",
        user_id="buyer-701",
        status="PENDING_PAYMENT",
        total_amount=Decimal("199.99"),
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(order)
    test_db_session.flush()

    order_item = OrderItem(
        id="item-701",
        order_id="order-701",
        product_id="prod-100",
        stock_id="stk-101",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("199.99"),
    )
    test_db_session.add(order_item)
    test_db_session.commit()

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to change name and price while illegally removing M
    res = client.patch(
        "/api/products/prod-100",
        headers=headers,
        json={
            "name": "Should Roll Back Name",
            "price": 999.99,
            "variants": [
                {"variant_key": "L", "available_quantity": 10},
            ],
        },
    )
    assert res.status_code == 409

    # Verify product in database was NOT updated
    test_db_session.expire_all()
    p = test_db_session.get(Product, "prod-100")
    assert p.name == "Leather Biker Jacket"
    assert p.price == Decimal("199.99")


def test_get_categories_endpoint(client):
    """GET /api/products/categories returns all 7 primary categories."""
    res = client.get("/api/products/categories")
    assert res.status_code == 200
    cats = res.json()
    expected = [
        "T-Shirts",
        "Shirts",
        "Hoodies & Sweatshirts",
        "Jackets",
        "Shorts",
        "Long Pants",
        "Accessories",
    ]
    assert cats == expected


def test_list_products_filter_by_tshirts_category(client, test_db_session):
    """GET /api/products?category=T-Shirts filters correctly and case-insensitively."""
    p_tshirt = Product(
        id="prod-tshirt-1",
        name="Classic Graphic Tee",
        description="Premium combed cotton tee.",
        price=Decimal("29.99"),
        stock_quantity=50,
        category="T-Shirts",
        seller_id="seller-100",
        is_active=True,
    )
    test_db_session.add(p_tshirt)
    test_db_session.commit()

    # Exact case
    res1 = client.get("/api/products?category=T-Shirts")
    assert res1.status_code == 200
    items1 = res1.json()
    assert any(item["id"] == "prod-tshirt-1" for item in items1)

    # Lower case
    res2 = client.get("/api/products?category=t-shirts")
    assert res2.status_code == 200
    items2 = res2.json()
    assert any(item["id"] == "prod-tshirt-1" for item in items2)

    # Unmatched category
    res3 = client.get("/api/products?category=Shorts")
    assert res3.status_code == 200
    items3 = res3.json()
    assert not any(item["id"] == "prod-tshirt-1" for item in items3)


def test_create_product_with_primary_categories(client, test_db_session):
    """Seller can create products using the primary marketplace categories."""
    from app.auth import create_access_token

    token = create_access_token({"sub": "test_seller@fashion.com"})
    headers = {"Authorization": f"Bearer {token}"}

    primary_categories = [
        "T-Shirts",
        "Shirts",
        "Hoodies & Sweatshirts",
        "Jackets",
        "Shorts",
        "Long Pants",
        "Accessories",
    ]

    for idx, cat in enumerate(primary_categories):
        payload = {
            "name": f"Test Item {cat}",
            "description": f"Quality {cat} item.",
            "price": 49.99 + idx,
            "stock_quantity": 10,
            "category": cat,
        }
        res = client.post("/api/products", headers=headers, json=payload)
        assert res.status_code == 201
        assert res.json()["category"] == cat


# ---------------------------------------------------------------------------
# FR-01: Prevent Sellers from Viewing Their Own Products in Shop
# ---------------------------------------------------------------------------

def test_seller_cannot_see_own_products_in_shop(client, test_db_session):
    """When a seller is logged in, their own products are hidden from GET /api/products."""
    from app.auth import create_access_token

    # Seed a 2nd seller and product owned by the 2nd seller
    now = datetime.now(timezone.utc)
    seller2 = User(
        id="seller-200",
        email="seller2@fashion.com",
        password_hash="hashed_pw",
        role="seller",
        created_at=now,
        updated_at=now,
    )
    p_other = Product(
        id="prod-other-200",
        name="Bohemian Maxi Dress",
        description="Silk bohemian dress.",
        price=Decimal("120.00"),
        stock_quantity=8,
        category="Dresses",
        seller_id="seller-200",
        is_active=True,
    )
    test_db_session.add_all([seller2, p_other])
    test_db_session.commit()

    # 1. Anonymous visitor sees all active products (including prod-100 and prod-other-200)
    res_anon = client.get("/api/products")
    assert res_anon.status_code == 200
    anon_ids = [p["id"] for p in res_anon.json()]
    assert "prod-100" in anon_ids  # Owned by seller-100
    assert "prod-other-200" in anon_ids  # Owned by seller-200

    # 2. Seller-100 logs in: prod-100 should be hidden, prod-other-200 should be visible
    seller1_token = create_access_token({"sub": "test_seller@fashion.com"})
    res_seller1 = client.get(
        "/api/products",
        headers={"Authorization": f"Bearer {seller1_token}"},
    )
    assert res_seller1.status_code == 200
    seller1_ids = [p["id"] for p in res_seller1.json()]
    assert "prod-100" not in seller1_ids
    assert "prod-other-200" in seller1_ids

    # 3. Seller-100 searches for their own product name: should return empty
    res_search = client.get(
        "/api/products?search=Leather+Biker",
        headers={"Authorization": f"Bearer {seller1_token}"},
    )
    assert res_search.status_code == 200
    assert len(res_search.json()) == 0

    # 4. Filter by category Jackets (which contains prod-100): should not show prod-100
    res_cat = client.get(
        "/api/products?category=Jackets",
        headers={"Authorization": f"Bearer {seller1_token}"},
    )
    assert res_cat.status_code == 200
    cat_ids = [p["id"] for p in res_cat.json()]
    assert "prod-100" not in cat_ids

    # 5. Buyer logs in: can see all products including prod-100 and prod-other-200
    buyer = User(
        id="buyer-100",
        email="buyer_test@fashion.com",
        password_hash="pw",
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    test_db_session.add(buyer)
    test_db_session.commit()

    buyer_token = create_access_token({"sub": "buyer_test@fashion.com"})
    res_buyer = client.get(
        "/api/products",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res_buyer.status_code == 200
    buyer_ids = [p["id"] for p in res_buyer.json()]
    assert "prod-100" in buyer_ids
    assert "prod-other-200" in buyer_ids






