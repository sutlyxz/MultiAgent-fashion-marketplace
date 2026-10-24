"""Contract and safety invariant tests for the PostgreSQL test harness.

These tests verify that:
1. TABLES_IN_CLEANUP_ORDER contains all 12 expected marketplace entities uniquely.
2. TABLES_IN_CLEANUP_ORDER strictly adheres to foreign-key hierarchy (child before parent)
   across all 18 relationships in models.py to prevent FK constraint violations during cleanup.
3. ALLOWED_TEST_DATABASE_NAME constant is strictly 'fashion_marketplace_test'.
4. validate_test_database_url rejects unsafe/invalid URLs and accepts allowlisted URLs.
5. All validations run purely in-memory without opening database connections, executing
   cleanup routines, or modifying persistent state.
"""

import os
import sys

import pytest

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from tests.postgres_test_harness import (
    ALLOWED_TEST_DATABASE_NAME,
    TABLES_IN_CLEANUP_ORDER,
    DatabaseSafetyError,
    validate_test_database_url,
)


EXPECTED_TABLE_SET = {
    "users",
    "products",
    "stocks",
    "checkout_sessions",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "support_tickets",
    "claims",
    "crm_tags",
    "user_crm_tags",
}

# All 18 Foreign-Key (child, parent) relationships defined in backend/app/models.py
FK_CHILD_PARENT_PAIRS = [
    ("user_crm_tags", "crm_tags"),       # UserCRMTag.tag_id -> CRMTag.id
    ("user_crm_tags", "users"),          # UserCRMTag.user_id -> User.id
    ("crm_tags", "users"),               # CRMTag.seller_id -> User.id
    ("claims", "orders"),                # Claim.order_id -> Order.id
    ("claims", "users"),                 # Claim.buyer_id & seller_id -> User.id
    ("support_tickets", "orders"),       # SupportTicket.order_id -> Order.id
    ("support_tickets", "users"),        # SupportTicket.user_id -> User.id
    ("shipments", "orders"),             # Shipment.order_id -> Order.id
    ("payments", "orders"),              # Payment.order_id -> Order.id
    ("order_items", "orders"),           # OrderItem.order_id -> Order.id
    ("order_items", "stocks"),           # OrderItem.stock_id -> Stock.id
    ("order_items", "products"),         # OrderItem.product_id -> Product.id
    ("orders", "users"),                 # Order.user_id -> User.id
    ("checkout_sessions", "stocks"),     # CheckoutSession.stock_id -> Stock.id
    ("checkout_sessions", "products"),   # CheckoutSession.product_id -> Product.id
    ("checkout_sessions", "users"),      # CheckoutSession.user_id -> User.id
    ("stocks", "products"),              # Stock.product_id -> Product.id
    ("products", "users"),               # Product.seller_id -> User.id
]


def test_cleanup_order_contains_all_12_known_tables_uniquely():
    """Verify that TABLES_IN_CLEANUP_ORDER has exactly 12 unique tables matching known models."""
    assert len(TABLES_IN_CLEANUP_ORDER) == 12, (
        f"Expected 12 tables in cleanup order, found {len(TABLES_IN_CLEANUP_ORDER)}"
    )
    assert len(set(TABLES_IN_CLEANUP_ORDER)) == 12, (
        "Duplicate table names found in TABLES_IN_CLEANUP_ORDER"
    )
    assert set(TABLES_IN_CLEANUP_ORDER) == EXPECTED_TABLE_SET, (
        f"Mismatch in expected table set: {set(TABLES_IN_CLEANUP_ORDER) ^ EXPECTED_TABLE_SET}"
    )


def test_cleanup_order_respects_foreign_key_hierarchy():
    """Verify that every child table appears before all its parent tables in TABLES_IN_CLEANUP_ORDER."""
    for child, parent in FK_CHILD_PARENT_PAIRS:
        child_idx = TABLES_IN_CLEANUP_ORDER.index(child)
        parent_idx = TABLES_IN_CLEANUP_ORDER.index(parent)
        assert child_idx < parent_idx, (
            f"Foreign key hierarchy violation: child table '{child}' (index {child_idx}) "
            f"must appear before parent table '{parent}' (index {parent_idx}) in TABLES_IN_CLEANUP_ORDER"
        )


def test_allowed_test_database_name_contract():
    """Verify that ALLOWED_TEST_DATABASE_NAME strictly enforces the test database name."""
    assert ALLOWED_TEST_DATABASE_NAME == "fashion_marketplace_test"
    assert ALLOWED_TEST_DATABASE_NAME.islower()
    assert " " not in ALLOWED_TEST_DATABASE_NAME


def test_validate_test_database_url_safety_rules():
    """Verify that validate_test_database_url rejects unsafe targets and accepts valid ones."""
    # 1. Missing or empty URL
    with pytest.raises(DatabaseSafetyError, match="TEST_DATABASE_URL is not set"):
        validate_test_database_url(None)
    with pytest.raises(DatabaseSafetyError, match="TEST_DATABASE_URL is not set"):
        validate_test_database_url("   ")

    # 2. Non-PostgreSQL scheme
    with pytest.raises(DatabaseSafetyError, match="valid PostgreSQL"):
        validate_test_database_url("sqlite:///fashion_marketplace_test.db")
    with pytest.raises(DatabaseSafetyError, match="valid PostgreSQL"):
        validate_test_database_url("mysql://localhost:3306/fashion_marketplace_test")

    # 3. Missing database name
    with pytest.raises(DatabaseSafetyError, match="does not specify a database name"):
        validate_test_database_url("postgresql://localhost:5432/")

    # 4. Development database name
    with pytest.raises(DatabaseSafetyError, match="fashion_marketplace_dev"):
        validate_test_database_url("postgresql://localhost:5432/fashion_marketplace_dev")

    # 5. Arbitrary database name not in allowlist
    with pytest.raises(DatabaseSafetyError, match="allowlist"):
        validate_test_database_url("postgresql://localhost:5432/unauthorized_db")

    # 6. Identical to dev_url
    dev_url = "postgresql://localhost:5432/fashion_marketplace_test"
    with pytest.raises(DatabaseSafetyError, match="identical"):
        validate_test_database_url(dev_url, dev_url=dev_url)

    # 7. Valid allowlisted test URL
    valid_url = "postgresql://user:pass@localhost:5432/fashion_marketplace_test"
    real_dev = "postgresql://user:pass@localhost:5432/fashion_marketplace_dev"
    assert validate_test_database_url(valid_url, dev_url=real_dev) == valid_url

    # 8. Case-insensitive acceptance
    upper_url = "postgresql://user:pass@localhost:5432/FASHION_MARKETPLACE_TEST"
    assert validate_test_database_url(upper_url, dev_url=real_dev) == upper_url


def test_harness_contracts_execute_without_network_or_db():
    """Verify that running contract checks has no environment or persistent side effects."""
    env_snapshot = dict(os.environ)
    valid_url = "postgresql://user:pass@localhost:5432/fashion_marketplace_test"
    result = validate_test_database_url(valid_url)
    assert result == valid_url
    assert os.environ == env_snapshot
