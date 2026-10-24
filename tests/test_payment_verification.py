from datetime import datetime
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import config
from app import database


@pytest.fixture
def pending_payment(monkeypatch):
    test_db = database.Database()
    monkeypatch.setattr(database, "db", test_db)
    monkeypatch.setattr(config.settings, "PAYMENT_RECIPIENT_ACCOUNT", "recipient-account")

    product_id = "test-product"
    stock_id = "test-stock"
    product = {
        "id": product_id,
        "name": "Classic Denim Jacket",
        "description": "A timeless denim jacket made from 100% organic cotton.",
        "price": 89.99,
        "stock_quantity": 10,
        "category": "Jackets",
        "seller_id": "11111111-1111-1111-1111-111111111111",
        "is_active": True,
    }
    test_db.products.append(product)

    stock = {
        "id": stock_id,
        "product_id": product_id,
        "variant_key": "M",
        "available_quantity": 10,
        "updated_at": datetime.utcnow(),
    }
    test_db.stocks.append(stock)

    order_id = "test-order"
    payment_id = "test-payment"
    order = {
        "id": order_id,
        "user_id": "buyer",
        "status": "PENDING_PAYMENT",
        "total_amount": 179.98,
        "updated_at": None,
    }
    test_db.orders.append(order)
    test_db.order_items.append(
        {
            "id": "test-order-item",
            "order_id": order_id,
            "product_id": stock["product_id"],
            "stock_id": stock["id"],
            "quantity": 2,
        }
    )
    payment = {
        "id": payment_id,
        "order_id": order_id,
        "slip_reference": "slip-reference",
        "slip_status": "UPLOADED",
        "verification_status": "UNAVAILABLE",
    }
    test_db.payments.append(payment)
    return test_db, order, payment, stock


def test_missing_verification_result_keeps_payment_unverified_and_stock_unchanged(
    pending_payment,
):
    test_db, order, payment, stock = pending_payment
    stock_before = stock["available_quantity"]

    result = database.verify_payment_and_decrement_stock(
        order["id"],
        payment["id"],
        payment["slip_reference"],
    )

    assert result["success"] is False
    assert "unavailable" in result["message"].casefold()
    assert payment["verification_status"] == "UNAVAILABLE"
    assert payment["slip_status"] == "UPLOADED"
    assert order["status"] == "PENDING_PAYMENT"
    assert stock["available_quantity"] == stock_before
    assert test_db.shipments == []


@pytest.mark.parametrize(
    "verification_result",
    [
        {
            "verified": False,
            "amount": "179.98",
            "destination_account": "recipient-account",
        },
        {
            "verified": True,
            "amount": "179.97",
            "destination_account": "recipient-account",
        },
        {
            "verified": True,
            "amount": "179.98",
            "destination_account": "different-account",
        },
    ],
)
def test_failed_or_mismatched_verification_never_deducts_stock(
    pending_payment,
    verification_result,
):
    _test_db, order, payment, stock = pending_payment
    stock_before = stock["available_quantity"]

    result = database.verify_payment_and_decrement_stock(
        order["id"],
        payment["id"],
        payment["slip_reference"],
        verification_result,
    )

    assert result["success"] is False
    assert payment["verification_status"] == "REJECTED"
    assert payment["slip_status"] == "REJECTED"
    assert order["status"] == "PENDING_PAYMENT"
    assert stock["available_quantity"] == stock_before


def test_verified_amount_and_recipient_are_required_before_stock_deduction(
    pending_payment,
):
    _test_db, order, payment, stock = pending_payment
    stock_before = stock["available_quantity"]

    result = database.verify_payment_and_decrement_stock(
        order["id"],
        payment["id"],
        payment["slip_reference"],
        {
            "verified": True,
            "amount": "179.98",
            "destination_account": "recipient-account",
            "reference": "verified-transaction",
        },
    )

    assert result["success"] is True
    assert payment["verification_status"] == "VERIFIED"
    assert payment["slip_status"] == "VERIFIED"
    assert payment["verification_reference"] == "verified-transaction"
    assert order["status"] == "PAID"
    assert stock["available_quantity"] == stock_before - 2
    assert result["receipt"]["order_id"] == order["id"]


def test_insufficient_stock_after_verification_does_not_issue_receipt(
    pending_payment,
):
    test_db, order, payment, stock = pending_payment
    stock["available_quantity"] = 1
    product = next(
        product for product in test_db.products if product["id"] == stock["product_id"]
    )
    product_stock_before = product["stock_quantity"]

    result = database.verify_payment_and_decrement_stock(
        order["id"],
        payment["id"],
        payment["slip_reference"],
        {
            "verified": True,
            "amount": "179.98",
            "destination_account": "recipient-account",
            "reference": "verified-transaction",
        },
    )

    assert result["success"] is False
    assert "insufficient stock" in result["message"].casefold()
    assert payment["verification_status"] == "VERIFIED"
    assert order["status"] == "MANUAL_RESOLUTION_REQUIRED"
    assert stock["available_quantity"] == 1
    assert product["stock_quantity"] == product_stock_before
    assert "receipt" not in result
    assert test_db.shipments == []


def test_duplicate_order_items_are_checked_as_one_stock_requirement(pending_payment):
    test_db, order, payment, stock = pending_payment
    stock_before = stock["available_quantity"]
    test_db.order_items.append(
        {
            "id": "duplicate-order-item",
            "order_id": order["id"],
            "product_id": stock["product_id"],
            "stock_id": stock["id"],
            "quantity": 9,
        }
    )

    result = database.verify_payment_and_decrement_stock(
        order["id"],
        payment["id"],
        payment["slip_reference"],
        {
            "verified": True,
            "amount": "179.98",
            "destination_account": "recipient-account",
        },
    )

    assert result["success"] is False
    assert order["status"] == "MANUAL_RESOLUTION_REQUIRED"
    assert stock["available_quantity"] == stock_before
    assert "receipt" not in result
