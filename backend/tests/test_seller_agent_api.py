"""Unit and API integration tests for Phase E:
Seller Operations (Claims & CRM Tags) and AI Agent Workflows (Claims & Logistics Tickets).

All tests use FastAPI TestClient with an isolated SQLite in-memory test database
(with PRAGMA foreign_keys=ON) overriding the `get_db` dependency.
No live or dev PostgreSQL database is modified.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token, hash_password
from app.database import db as in_memory_db
from app.db_connection import Base, get_db
from app.main import app
from app.models import (
    Claim,
    CRMTag,
    Order,
    OrderItem,
    Product,
    Shipment,
    Stock,
    SupportTicket,
    User,
    UserCRMTag,
)


@pytest.fixture
def test_db_session():
    """Create isolated SQLite in-memory database with SQLite foreign keys enabled."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    # 1. Seed Users
    buyer1 = User(
        id="usr-buyer-1",
        email="buyer1_e@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    buyer2 = User(
        id="usr-buyer-2",
        email="buyer2_e@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    seller1 = User(
        id="usr-seller-1",
        email="seller1_e@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    seller2 = User(
        id="usr-seller-2",
        email="seller2_e@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add_all([buyer1, buyer2, seller1, seller2])
    session.flush()

    # 2. Seed Products
    prod1 = Product(
        id="prod-e-1",
        name="Silk Dress",
        description="Luxury silk",
        price=Decimal("120.00"),
        stock_quantity=10,
        category="Dresses",
        seller_id="usr-seller-1",
        is_active=True,
    )
    prod2 = Product(
        id="prod-e-2",
        name="Leather Boots",
        description="Handcrafted boots",
        price=Decimal("200.00"),
        stock_quantity=5,
        category="Shoes",
        seller_id="usr-seller-2",
        is_active=True,
    )
    session.add_all([prod1, prod2])
    session.flush()

    # 3. Seed Stocks
    stock1 = Stock(
        id="stk-e-1",
        product_id="prod-e-1",
        variant_key="M",
        available_quantity=10,
        updated_at=now,
    )
    stock2 = Stock(
        id="stk-e-2",
        product_id="prod-e-2",
        variant_key="42",
        available_quantity=5,
        updated_at=now,
    )
    session.add_all([stock1, stock2])
    session.flush()

    # 4. Seed Orders & OrderItems
    order1 = Order(
        id="ord-e-1",
        user_id="usr-buyer-1",
        status="PAID",
        total_amount=Decimal("120.00"),
        created_at=now,
        updated_at=now,
    )
    order2 = Order(
        id="ord-e-2",
        user_id="usr-buyer-2",
        status="PAID",
        total_amount=Decimal("200.00"),
        created_at=now,
        updated_at=now,
    )
    session.add_all([order1, order2])
    session.flush()

    item1 = OrderItem(
        id="item-e-1",
        order_id="ord-e-1",
        product_id="prod-e-1",
        stock_id="stk-e-1",
        variant_key="M",
        quantity=1,
        unit_price=Decimal("120.00"),
    )
    item2 = OrderItem(
        id="item-e-2",
        order_id="ord-e-2",
        product_id="prod-e-2",
        stock_id="stk-e-2",
        variant_key="42",
        quantity=1,
        unit_price=Decimal("200.00"),
    )
    session.add_all([item1, item2])
    session.flush()

    # 5. Seed Shipment
    shipment1 = Shipment(
        id="shp-e-1",
        order_id="ord-e-1",
        carrier_name="FashionExpress",
        tracking_number="FE-TRACK-100",
        status="PREPARING",
        estimated_delivery=now,
        created_at=now,
    )
    session.add(shipment1)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(test_db_session):
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
    return create_access_token({"sub": "buyer1_e@fashion.com"})


@pytest.fixture
def buyer2_token():
    return create_access_token({"sub": "buyer2_e@fashion.com"})


@pytest.fixture
def seller1_token():
    return create_access_token({"sub": "seller1_e@fashion.com"})


@pytest.fixture
def seller2_token():
    return create_access_token({"sub": "seller2_e@fashion.com"})


# =========================================================================== #
# CLAIMS TESTS
# =========================================================================== #

def test_submit_claim_and_read_from_postgres(client, test_db_session, buyer1_token):
    """1. Buyer submits claim; record is stored in DB with derived seller_id."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    payload = {
        "order_id": "ord-e-1",
        "reason": "The silk dress has a torn seam defect on arrival",
    }
    resp = client.post("/api/agent/claim/submit", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_id"] == "ord-e-1"
    assert data["buyer_id"] == "usr-buyer-1"
    assert data["seller_id"] == "usr-seller-1"
    assert data["status"] == "PENDING"
    assert "APPROVE" in data["ai_recommendation"]

    # Verify directly in SQLite test database
    claim = test_db_session.scalar(select(Claim).where(Claim.id == data["id"]))
    assert claim is not None
    assert claim.seller_id == "usr-seller-1"
    assert claim.status == "PENDING"


def test_seller_sees_only_own_pending_claims(client, test_db_session, buyer1_token, seller1_token, seller2_token):
    """2. Seller only sees pending claims for products they sold."""
    # Buyer1 submits claim for seller1's product
    headers_buyer = {"Authorization": f"Bearer {buyer1_token}"}
    client.post("/api/agent/claim/submit", json={"order_id": "ord-e-1", "reason": "Defective item"}, headers=headers_buyer)

    # Seller1 checks pending claims -> 1 claim found
    resp1 = client.get("/api/seller/pending-claims", headers={"Authorization": f"Bearer {seller1_token}"})
    assert resp1.status_code == 200
    claims1 = resp1.json()
    assert len(claims1) == 1
    assert claims1[0]["order_id"] == "ord-e-1"

    # Seller2 checks pending claims -> 0 claims found (isolation)
    resp2 = client.get("/api/seller/pending-claims", headers={"Authorization": f"Bearer {seller2_token}"})
    assert resp2.status_code == 200
    claims2 = resp2.json()
    assert len(claims2) == 0


def test_seller_approves_own_claim(client, test_db_session, buyer1_token, seller1_token):
    """3. Seller approves their own claim; status becomes APPROVED with reviewed_at."""
    client.post("/api/agent/claim/submit", json={"order_id": "ord-e-1", "reason": "Broken zipper"}, headers={"Authorization": f"Bearer {buyer1_token}"})
    claim = test_db_session.scalar(select(Claim).where(Claim.order_id == "ord-e-1"))

    resp = client.post(
        f"/api/seller/claims/{claim.id}/approve",
        json={"comments": "Accepted refund request"},
        headers={"Authorization": f"Bearer {seller1_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert "Seller Comments: Accepted refund request" in data["reason"]
    assert data["reviewed_at"] is not None

    test_db_session.refresh(claim)
    assert claim.status == "APPROVED"
    assert claim.reviewed_at is not None


def test_seller_rejects_own_claim(client, test_db_session, buyer1_token, seller1_token):
    """4. Seller rejects their own claim; status becomes REJECTED."""
    client.post("/api/agent/claim/submit", json={"order_id": "ord-e-1", "reason": "Changed my mind"}, headers={"Authorization": f"Bearer {buyer1_token}"})
    claim = test_db_session.scalar(select(Claim).where(Claim.order_id == "ord-e-1"))

    resp = client.post(
        f"/api/seller/claims/{claim.id}/reject",
        json={"comments": "Not a manufacturing defect"},
        headers={"Authorization": f"Bearer {seller1_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert "Seller Comments: Not a manufacturing defect" in data["reason"]

    test_db_session.refresh(claim)
    assert claim.status == "REJECTED"


def test_seller_cannot_approve_or_reject_other_seller_claim(client, test_db_session, buyer1_token, seller2_token):
    """5. Seller cannot approve or reject another seller's claim."""
    client.post("/api/agent/claim/submit", json={"order_id": "ord-e-1", "reason": "Torn sleeve"}, headers={"Authorization": f"Bearer {buyer1_token}"})
    claim = test_db_session.scalar(select(Claim).where(Claim.order_id == "ord-e-1"))

    # Seller2 attempts to approve Seller1's claim -> 403 Forbidden
    resp_approve = client.post(
        f"/api/seller/claims/{claim.id}/approve",
        json={"comments": "I approve"},
        headers={"Authorization": f"Bearer {seller2_token}"},
    )
    assert resp_approve.status_code == 403
    assert "permission" in resp_approve.json()["detail"].lower()

    # Seller2 attempts to reject Seller1's claim -> 403 Forbidden
    resp_reject = client.post(
        f"/api/seller/claims/{claim.id}/reject",
        json={"comments": "I reject"},
        headers={"Authorization": f"Bearer {seller2_token}"},
    )
    assert resp_reject.status_code == 403

    test_db_session.refresh(claim)
    assert claim.status == "PENDING"


def test_claim_foreign_keys_and_buyer_ownership(client, buyer1_token, buyer2_token):
    """6. Buyer cannot submit claim for an order they do not own, or nonexistent order."""
    # Buyer2 tries to submit claim for Buyer1's order -> 403 Forbidden
    resp_forbidden = client.post(
        "/api/agent/claim/submit",
        json={"order_id": "ord-e-1", "reason": "Defective"},
        headers={"Authorization": f"Bearer {buyer2_token}"},
    )
    assert resp_forbidden.status_code == 403

    # Buyer1 tries to submit claim for nonexistent order -> 404 Not Found
    resp_notfound = client.post(
        "/api/agent/claim/submit",
        json={"order_id": "nonexistent-order-id", "reason": "Defective"},
        headers={"Authorization": f"Bearer {buyer1_token}"},
    )
    assert resp_notfound.status_code == 404


# =========================================================================== #
# CRM TAGS TESTS
# =========================================================================== #

def test_create_and_list_crm_tags(client, test_db_session, seller1_token):
    """8. Seller creates CRM tag and lists it from PostgreSQL-backed session."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    resp = client.post("/api/seller/crm-tags", json={"name": "VIP Customer"}, headers=headers)
    assert resp.status_code == 200
    tag_data = resp.json()
    assert tag_data["name"] == "VIP Customer"
    assert tag_data["seller_id"] == "usr-seller-1"

    # List tags
    list_resp = client.get("/api/seller/crm-tags", headers=headers)
    assert list_resp.status_code == 200
    tags = list_resp.json()
    assert any(t["id"] == tag_data["id"] for t in tags)

    # Verify directly in SQLite
    tag = test_db_session.scalar(select(CRMTag).where(CRMTag.id == tag_data["id"]))
    assert tag is not None
    assert tag.name == "VIP Customer"


def test_duplicate_crm_tag_exact_prevented(client, seller1_token):
    """9. Exact duplicate tag name under same seller is rejected."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    client.post("/api/seller/crm-tags", json={"name": "Wholesale"}, headers=headers)
    resp_dup = client.post("/api/seller/crm-tags", json={"name": "Wholesale"}, headers=headers)
    assert resp_dup.status_code == 400
    assert resp_dup.json()["detail"] == "CRM Tag with this name already exists"


def test_duplicate_crm_tag_case_insensitive_prevented(client, seller1_token):
    """10. Case-insensitive duplicate tag name under same seller is rejected."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    client.post("/api/seller/crm-tags", json={"name": "Loyal Buyer"}, headers=headers)

    # Try different casing
    resp_lower = client.post("/api/seller/crm-tags", json={"name": "loyal buyer"}, headers=headers)
    assert resp_lower.status_code == 400
    assert resp_lower.json()["detail"] == "CRM Tag with this name already exists"

    resp_mixed = client.post("/api/seller/crm-tags", json={"name": "LoYaL BuYeR"}, headers=headers)
    assert resp_mixed.status_code == 400


def test_seller_crm_tag_isolation(client, seller1_token, seller2_token):
    """11. Seller2 cannot view or associate Seller1's tag, but can have same name tag."""
    headers1 = {"Authorization": f"Bearer {seller1_token}"}
    headers2 = {"Authorization": f"Bearer {seller2_token}"}

    # Seller1 creates "Special"
    resp1 = client.post("/api/seller/crm-tags", json={"name": "Special"}, headers=headers1)
    tag1_id = resp1.json()["id"]

    # Seller2 can create their own "Special" tag (scoped per seller)
    resp2 = client.post("/api/seller/crm-tags", json={"name": "Special"}, headers=headers2)
    assert resp2.status_code == 200
    tag2_id = resp2.json()["id"]
    assert tag1_id != tag2_id

    # Seller2 cannot associate Seller1's tag
    assoc_resp = client.post(
        f"/api/seller/customers/usr-buyer-1/tags/{tag1_id}",
        headers=headers2,
    )
    assert assoc_resp.status_code == 403
    assert "You do not own this CRM tag" in assoc_resp.json()["detail"]


def test_associate_crm_tag_to_customer_and_prevent_duplicate(client, test_db_session, seller1_token):
    """12 & 13. Associating tag creates UserCRMTag; duplicate association is idempotent."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    tag_resp = client.post("/api/seller/crm-tags", json={"name": "Frequent"}, headers=headers)
    tag_id = tag_resp.json()["id"]

    # First association
    assoc1 = client.post(f"/api/seller/customers/usr-buyer-1/tags/{tag_id}", headers=headers)
    assert assoc1.status_code == 200
    assert assoc1.json()["success"] is True

    # Check row in DB
    user_tag = test_db_session.scalar(
        select(UserCRMTag).where(UserCRMTag.user_id == "usr-buyer-1", UserCRMTag.tag_id == tag_id)
    )
    assert user_tag is not None

    # Second association (idempotent duplicate)
    assoc2 = client.post(f"/api/seller/customers/usr-buyer-1/tags/{tag_id}", headers=headers)
    assert assoc2.status_code == 200
    assert assoc2.json()["success"] is True

    # Count rows in DB - still exactly 1
    count = len(test_db_session.scalars(
        select(UserCRMTag).where(UserCRMTag.user_id == "usr-buyer-1", UserCRMTag.tag_id == tag_id)
    ).all())
    assert count == 1


def test_associate_crm_tag_invalid_user_or_tag_rejected(client, seller1_token):
    """14. Invalid user or tag is rejected cleanly."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    tag_resp = client.post("/api/seller/crm-tags", json={"name": "Promo"}, headers=headers)
    tag_id = tag_resp.json()["id"]

    # Nonexistent customer -> 404
    resp_user_404 = client.post(f"/api/seller/customers/nonexistent-usr/tags/{tag_id}", headers=headers)
    assert resp_user_404.status_code == 404
    assert resp_user_404.json()["detail"] == "Customer not found"

    # Nonexistent tag -> 403
    resp_tag_403 = client.post("/api/seller/customers/usr-buyer-1/tags/nonexistent-tag", headers=headers)
    assert resp_tag_403.status_code == 403


# =========================================================================== #
# SUPPORT TICKETS & AGENT LOGISTICS TESTS
# =========================================================================== #

def test_logistics_check_creates_ticket_on_anomaly(client, test_db_session, buyer1_token):
    """15 & 16. Logistics check on PREPARING status creates SupportTicket for order."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    resp = client.post(
        "/api/agent/logistics/check-and-ticket",
        json={"tracking_number": "FE-TRACK-100"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["anomaly_detected"] is True
    assert data["ticket_created"] is True
    assert data["ticket_id"] is not None
    assert "anomaly detected" in data["message"].lower()

    # Check DB SupportTicket
    ticket = test_db_session.scalar(select(SupportTicket).where(SupportTicket.id == data["ticket_id"]))
    assert ticket is not None
    assert ticket.order_id == "ord-e-1"
    assert ticket.user_id == "usr-buyer-1"
    assert ticket.type == "LOGISTICS_ANOMALY"
    assert ticket.status == "OPEN"


def test_logistics_check_retry_does_not_duplicate_ticket(client, test_db_session, buyer1_token):
    """18. Retrying check on same shipment does not create a second ticket."""
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    # First call creates ticket
    resp1 = client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-TRACK-100"}, headers=headers)
    ticket_id = resp1.json()["ticket_id"]

    # Second call detects existing ticket
    resp2 = client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-TRACK-100"}, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["anomaly_detected"] is True
    assert data2["ticket_created"] is False
    assert data2["ticket_id"] == ticket_id
    assert "already been created" in data2["message"]

    # Verify count in DB is 1
    tickets = test_db_session.scalars(select(SupportTicket).where(SupportTicket.order_id == "ord-e-1")).all()
    assert len(tickets) == 1


def test_logistics_check_on_track_does_not_create_ticket(client, test_db_session, buyer1_token):
    """19. When shipment is on track (DELIVERED), no ticket is created."""
    shipment = test_db_session.scalar(select(Shipment).where(Shipment.tracking_number == "FE-TRACK-100"))
    shipment.status = "DELIVERED"
    test_db_session.commit()

    headers = {"Authorization": f"Bearer {buyer1_token}"}
    resp = client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-TRACK-100"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["anomaly_detected"] is False
    assert data["ticket_created"] is False
    assert data["ticket_id"] is None
    assert "on track" in data["message"].lower()

    # DB has no tickets for ord-e-1
    count = len(test_db_session.scalars(select(SupportTicket).where(SupportTicket.order_id == "ord-e-1")).all())
    assert count == 0


def test_logistics_check_unauthorized_user_forbidden(client, buyer2_token):
    """17. Buyer2 cannot check shipment belonging to Buyer1's order."""
    headers = {"Authorization": f"Bearer {buyer2_token}"}
    resp = client.post(
        "/api/agent/logistics/check-and-ticket",
        json={"tracking_number": "FE-TRACK-100"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()


def test_logistics_check_seller_allowed(client, seller1_token):
    """Seller can check shipment for their order."""
    headers = {"Authorization": f"Bearer {seller1_token}"}
    resp = client.post(
        "/api/agent/logistics/check-and-ticket",
        json={"tracking_number": "FE-TRACK-100"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["anomaly_detected"] is True


def test_in_memory_db_collections_not_written(client, buyer1_token, seller1_token):
    """20. Verified that migrated endpoints do not write to in_memory_db."""
    initial_claims_len = len(in_memory_db.claims)
    initial_tags_len = len(in_memory_db.crm_tags)
    initial_assoc_len = len(in_memory_db.user_crm_tags)
    initial_tickets_len = len(in_memory_db.support_tickets)

    # Submit claim
    client.post("/api/agent/claim/submit", json={"order_id": "ord-e-1", "reason": "Defect"}, headers={"Authorization": f"Bearer {buyer1_token}"})
    # Create tag
    tag_resp = client.post("/api/seller/crm-tags", json={"name": "InMemCheck"}, headers={"Authorization": f"Bearer {seller1_token}"})
    tag_id = tag_resp.json()["id"]
    # Associate tag
    client.post(f"/api/seller/customers/usr-buyer-1/tags/{tag_id}", headers={"Authorization": f"Bearer {seller1_token}"})
    # Check logistics
    client.post("/api/agent/logistics/check-and-ticket", json={"tracking_number": "FE-TRACK-100"}, headers={"Authorization": f"Bearer {buyer1_token}"})

    # Assert in-memory collections remained unchanged
    assert len(in_memory_db.claims) == initial_claims_len
    assert len(in_memory_db.crm_tags) == initial_tags_len
    assert len(in_memory_db.user_crm_tags) == initial_assoc_len
    assert len(in_memory_db.support_tickets) == initial_tickets_len


def test_chat_endpoint_remains_functional(client):
    """21. Chat endpoint continues to work as expected."""
    resp = client.post("/api/agent/chat", json={"message": "I received a broken item"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data["suggested_action"] == "SUBMIT_WARRANTY_CLAIM"
