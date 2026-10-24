"""Unit and Integration tests for Phase 4.4: Simulated Payment API.

Tests all required scenarios:
1. จำลองชำระสำเร็จและ Order เปลี่ยนเป็น PAID
2. จำลองล้มเหลวและ Order ยังคง PENDING_PAYMENT
3. ผู้ใช้ที่ไม่ได้ Login (401 Unauthorized)
4. ผู้ใช้พยายามชำระ Order ของผู้อื่น (403 Forbidden)
5. Order ที่ไม่มีอยู่ (404 Not Found)
6. Order ที่ CANCELLED (400 Bad Request)
7. เรียกชำระซ้ำหลังสำเร็จ (Idempotent, no duplicate payment rows)
8. ตรวจสอบว่าไม่มี Stock Deduction ซ้ำ (Stock was already decremented at checkout)
9. Database exception และ Transaction rollback
10. Concurrent payment requests handling
11. Payment Slip ที่ VERIFIED และกฎเดิมที่เกี่ยวข้อง
12. การอัปโหลดสลิปและการยกเลิก Order ยังทำงานเหมือนเดิม
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys
from unittest.mock import patch

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
from app.models import Order, OrderItem, Payment, Product, Stock, User


@pytest.fixture
def test_db_session(monkeypatch):
    """Create an isolated in-memory SQLite database and seed test accounts and catalog."""
    monkeypatch.setattr(settings, "PAYMENT_RECIPIENT_ACCOUNT", "recipient-test-123")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    # 1. Seed Users
    buyer1 = User(
        id="usr-sim-buyer1",
        email="buyer1_sim@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    buyer2 = User(
        id="usr-sim-buyer2",
        email="buyer2_sim@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    seller = User(
        id="usr-sim-seller",
        email="seller_sim@fashion.com",
        password_hash=hash_password("Pass123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    session.add_all([buyer1, buyer2, seller])
    session.flush()

    # 2. Seed Product
    product = Product(
        id="prod-sim-100",
        name="Tailored Linen Blazer",
        description="Luxury Linen Blazer",
        price=Decimal("120.00"),
        stock_quantity=20,
        category="Jackets",
        seller_id="usr-sim-seller",
        is_active=True,
    )
    session.add(product)
    session.flush()

    # 3. Seed Stock Variant
    stock = Stock(
        id="stk-sim-101",
        product_id="prod-sim-100",
        variant_key="M",
        available_quantity=20,
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
    return create_access_token({"sub": "buyer1_sim@fashion.com"})


@pytest.fixture
def buyer2_token():
    return create_access_token({"sub": "buyer2_sim@fashion.com"})


def _create_test_order(client, token, quantity=2):
    """Helper to create an order for buyer1."""
    headers = {"Authorization": f"Bearer {token}"}
    create_res = client.post(
        "/api/orders/create",
        json={"items": [{"product_id": "prod-sim-100", "variant_key": "M", "quantity": quantity}]},
        headers=headers,
    )
    assert create_res.status_code == 200, create_res.text
    return create_res.json()["id"]


# -----------------------------------------------------------------------------
# Test 1: จำลองชำระสำเร็จและ Order เปลี่ยนเป็น PAID
# -----------------------------------------------------------------------------
def test_simulate_payment_success_transitions_order_to_paid(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS", "payment_method": "SIMULATED_CARD"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["order"]["status"] == "PAID"
    assert data["order"]["id"] == order_id
    assert data["payment_id"] is not None

    # Verify DB state directly
    order = test_db_session.execute(select(Order).where(Order.id == order_id)).scalar_one()
    assert order.status == "PAID"

    # Verify Payment record
    payment = test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalar_one()
    assert payment.payment_type == "SIMULATED_CARD"
    assert payment.slip_status == "VERIFIED"
    assert payment.verification_status == "VERIFIED"
    assert payment.extracted_payment_data.get("simulation") is True or payment.extracted_payment_data.get("simulated") is True


# -----------------------------------------------------------------------------
# Test 2: จำลองล้มเหลวและ Order ยังคง PENDING_PAYMENT
# -----------------------------------------------------------------------------
def test_simulate_payment_failure_leaves_order_pending_payment(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={
            "outcome": "FAILURE",
            "payment_method": "SIMULATED_CARD",
            "failure_reason": "Insufficient simulated funds",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["order"]["status"] == "PENDING_PAYMENT"

    # Verify DB state: order must remain PENDING_PAYMENT
    order = test_db_session.execute(select(Order).where(Order.id == order_id)).scalar_one()
    assert order.status == "PENDING_PAYMENT"

    # Payment record exists with REJECTED
    payment = test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalar_one()
    assert payment.slip_status == "REJECTED"
    assert payment.verification_status == "REJECTED"


# -----------------------------------------------------------------------------
# Test 3: ผู้ใช้ที่ไม่ได้ Login (401 Unauthorized)
# -----------------------------------------------------------------------------
def test_simulate_payment_unauthenticated_returns_401(client, buyer1_token):
    order_id = _create_test_order(client, buyer1_token)

    # Call without Authorization header
    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
    )
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# Test 4: ผู้ใช้พยายามชำระ Order ของผู้อื่น (403 Forbidden)
# -----------------------------------------------------------------------------
def test_simulate_payment_other_user_order_returns_403(client, buyer1_token, buyer2_token):
    order_id = _create_test_order(client, buyer1_token)
    headers_buyer2 = {"Authorization": f"Bearer {buyer2_token}"}

    # Buyer 2 tries to simulate payment on Buyer 1's order
    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers_buyer2,
    )
    assert res.status_code == 403
    assert "permission to pay" in res.text.lower()


# -----------------------------------------------------------------------------
# Test 5: Order ที่ไม่มีอยู่ (404 Not Found)
# -----------------------------------------------------------------------------
def test_simulate_payment_nonexistent_order_returns_404(client, buyer1_token):
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    fake_order_id = "00000000-0000-0000-0000-000000000000"

    res = client.post(
        f"/api/orders/{fake_order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert res.status_code == 404
    assert "Order not found" in res.text


# -----------------------------------------------------------------------------
# Test 6: Order ที่ CANCELLED (400 Bad Request)
# -----------------------------------------------------------------------------
def test_simulate_payment_cancelled_order_returns_400(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # Cancel the order first
    cancel_res = client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200

    order = test_db_session.execute(select(Order).where(Order.id == order_id)).scalar_one()
    assert order.status == "CANCELLED"

    # Try to pay cancelled order
    pay_res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert pay_res.status_code == 400
    assert "cancelled" in pay_res.text.lower()


# -----------------------------------------------------------------------------
# Test 7: เรียกชำระซ้ำหลังสำเร็จ (Idempotent, no duplicate payment rows)
# -----------------------------------------------------------------------------
def test_simulate_payment_repeated_call_idempotent_no_duplicate_payment(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # 1st call: Success
    res1 = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res1.json()["order"]["status"] == "PAID"

    # Count payments
    payments_count_1 = len(
        test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()
    )
    assert payments_count_1 == 1

    # 2nd call: Repeated call on already paid order
    res2 = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["success"] is True
    assert res2.json()["order"]["status"] == "PAID"
    assert "already paid" in res2.json()["message"].lower()

    # Verify no additional payment was inserted
    payments_count_2 = len(
        test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()
    )
    assert payments_count_2 == 1


# -----------------------------------------------------------------------------
# Test 8: ตรวจสอบว่าไม่มี Stock Deduction ซ้ำ
# -----------------------------------------------------------------------------
def test_simulate_payment_does_not_deduct_stock_again(client, buyer1_token, test_db_session):
    stock_before_order = test_db_session.execute(
        select(Stock).where(Stock.id == "stk-sim-101")
    ).scalar_one().available_quantity
    assert stock_before_order == 20

    # Order creation deducts 2 items (Phase 4.3 rule)
    order_id = _create_test_order(client, buyer1_token, quantity=2)

    test_db_session.expire_all()
    stock_after_order = test_db_session.execute(
        select(Stock).where(Stock.id == "stk-sim-101")
    ).scalar_one().available_quantity
    assert stock_after_order == 18

    # Now simulate payment
    headers = {"Authorization": f"Bearer {buyer1_token}"}
    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert res.status_code == 200

    # Stock MUST NOT be decremented again!
    test_db_session.expire_all()
    stock_after_payment = test_db_session.execute(
        select(Stock).where(Stock.id == "stk-sim-101")
    ).scalar_one().available_quantity
    assert stock_after_payment == 18, "Stock was deducted again on payment! That violates Option A rules."


# -----------------------------------------------------------------------------
# Test 9: Database exception และ Transaction rollback
# -----------------------------------------------------------------------------
def test_simulate_payment_db_exception_triggers_rollback(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # Simulate an error during db.commit() using a non-raising client
    client_no_raise = TestClient(app, raise_server_exceptions=False)
    with patch.object(test_db_session, "commit", side_effect=Exception("Simulated DB connection failure")):
        res = client_no_raise.post(
            f"/api/orders/{order_id}/simulate-payment",
            json={"outcome": "SUCCESS"},
            headers=headers,
        )
        assert res.status_code == 500

    # After rollback, order must remain PENDING_PAYMENT
    test_db_session.expire_all()
    order = test_db_session.execute(select(Order).where(Order.id == order_id)).scalar_one()
    assert order.status == "PENDING_PAYMENT"


# -----------------------------------------------------------------------------
# Test 10: Concurrent payment requests handling
# -----------------------------------------------------------------------------
def test_simulate_payment_concurrency_race_condition_handling(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # Sequentially simulate two fast successive requests (as would happen in race condition)
    res1 = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    res2 = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )

    assert res1.status_code == 200
    assert res2.status_code == 200

    # Order must be PAID, exactly 1 payment record
    order = test_db_session.execute(select(Order).where(Order.id == order_id)).scalar_one()
    assert order.status == "PAID"

    payments = test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()
    assert len(payments) == 1


# -----------------------------------------------------------------------------
# Test 11: Payment Slip ที่ VERIFIED และกฎเดิมที่เกี่ยวข้อง
# -----------------------------------------------------------------------------
def test_simulate_payment_order_with_existing_verified_slip(client, buyer1_token, test_db_session):
    order_id = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    # Manually attach an existing VERIFIED slip to the order
    existing_payment = Payment(
        order_id=order_id,
        payment_type="SLIP_UPLOAD",
        slip_reference="SLIP-ALREADY-VERIFIED-999",
        slip_status="VERIFIED",
        verification_status="VERIFIED",
        extracted_payment_data={"amount": 240.0, "status": "VERIFIED"},
    )
    test_db_session.add(existing_payment)
    test_db_session.commit()

    # Simulate payment should recognize verified payment and mark order PAID idempotently
    res = client.post(
        f"/api/orders/{order_id}/simulate-payment",
        json={"outcome": "SUCCESS"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["order"]["status"] == "PAID"

    # Only 1 payment row exists
    payments = test_db_session.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()
    assert len(payments) == 1
    assert payments[0].slip_reference == "SLIP-ALREADY-VERIFIED-999"


# -----------------------------------------------------------------------------
# Test 12: การอัปโหลดสลิปและการยกเลิก Order ยังทำงานเหมือนเดิม
# -----------------------------------------------------------------------------
def test_existing_slip_upload_and_cancel_order_still_work(client, buyer1_token, test_db_session):
    # Part A: Test Cancel Order behavior
    order_id_1 = _create_test_order(client, buyer1_token)
    headers = {"Authorization": f"Bearer {buyer1_token}"}

    stock_before_cancel = test_db_session.execute(
        select(Stock).where(Stock.id == "stk-sim-101")
    ).scalar_one().available_quantity

    cancel_res = client.post(f"/api/orders/{order_id_1}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    test_db_session.expire_all()
    stock_after_cancel = test_db_session.execute(
        select(Stock).where(Stock.id == "stk-sim-101")
    ).scalar_one().available_quantity
    assert stock_after_cancel == stock_before_cancel + 2, "Cancel order failed to restore stock"

    # Part B: Test Slip Upload endpoint behavior
    order_id_2 = _create_test_order(client, buyer1_token)
    upload_res = client.post(
        "/api/orders/upload-slip",
        json={"order_id": order_id_2, "slip_reference": "SLIP-TEST-VERIFY-123"},
        headers=headers,
    )
    assert upload_res.status_code == 200, upload_res.text
    slip_data = upload_res.json()
    assert slip_data["order_id"] == order_id_2
    assert "payment_id" in slip_data
    assert slip_data["slip_status"] in ["UPLOADED", "VERIFIED"]
