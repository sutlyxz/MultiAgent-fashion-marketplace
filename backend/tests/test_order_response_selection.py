"""Phase D.1 tests: deterministic Payment/Shipment selection in Order responses.

Order.payments / Order.shipments are 1:N collections whose ORM order is not
guaranteed. ``_format_order`` must pick the latest record by
``(created_at, id)`` and still return a single object (or None), per the
existing API contract.

All DB-backed tests use an isolated SQLite in-memory database via a
``get_db`` dependency override. They do NOT exercise PostgreSQL; the
migration tests are static (source/AST) checks and do not run Alembic.
"""

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import class_mapper, configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token, hash_password
from app.db_connection import Base, get_db
from app.main import app
from app.models import Order, OrderItem, Payment, Product, Shipment, Stock, User
from app.routers.orders import _format_order
from app.schemas import OrderResponse

VERSIONS_DIR = os.path.join(BACKEND_DIR, "migrations", "versions")
INITIAL_MIGRATION = os.path.join(VERSIONS_DIR, "d6931d9c9757_initial_schema.py")
SHIPMENT_MIGRATION = os.path.join(
    VERSIONS_DIR, "7b2e4c1a9f30_add_shipments_created_at.py"
)
PROFILE_MEDIA_MIGRATION = os.path.join(
    VERSIONS_DIR, "c3a8e1b2f904_add_user_profile_and_product_media.py"
)

BASE_TIME = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
BUYER_EMAIL = "buyer_sel@fashion.com"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    s.add_all([
        User(id="usr-sel-buyer", email=BUYER_EMAIL,
             password_hash=hash_password("Pass123!"), role="buyer",
             created_at=BASE_TIME, updated_at=BASE_TIME),
        User(id="usr-sel-seller", email="seller_sel@fashion.com",
             password_hash=hash_password("Pass123!"), role="seller",
             created_at=BASE_TIME, updated_at=BASE_TIME),
    ])
    s.flush()
    s.add(Product(id="prod-sel", name="Linen Shirt", description="d",
                  price=Decimal("30.00"), stock_quantity=5, category="Shirts",
                  seller_id="usr-sel-seller", is_active=True))
    s.flush()
    s.add(Stock(id="stk-sel", product_id="prod-sel", variant_key="M",
                available_quantity=5, updated_at=BASE_TIME))
    s.flush()
    order = Order(id="ord-sel", user_id="usr-sel-buyer", status="PENDING_PAYMENT",
                  total_amount=Decimal("30.00"),
                  created_at=BASE_TIME, updated_at=BASE_TIME)
    order.items.append(OrderItem(id="oi-sel", product_id="prod-sel",
                                 stock_id="stk-sel", variant_key="M",
                                 quantity=1, unit_price=Decimal("30.00")))
    s.add(order)
    s.commit()
    try:
        yield s
    finally:
        s.close()
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
def auth_headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': BUYER_EMAIL})}"}


def _payment(pid, created_at):
    return Payment(id=pid, order_id="ord-sel", payment_type="BANK_TRANSFER",
                   slip_reference=f"slip-{pid}", slip_status="UPLOADED",
                   verification_status="UNAVAILABLE", created_at=created_at)


def _shipment(sid, created_at):
    return Shipment(id=sid, order_id="ord-sel", carrier_name="FashionExpress",
                    tracking_number=f"FE-{sid}", status="PREPARING",
                    estimated_delivery=BASE_TIME + timedelta(days=3),
                    created_at=created_at)


def _reload_order(session):
    session.expire_all()
    return session.get(Order, "ord-sel")


# --------------------------------------------------------------------------- #
# 1-2. Payment selection
# --------------------------------------------------------------------------- #

def test_latest_payment_selected_by_created_at(session):
    # Insert newest first so collection order would mislead any [-1] logic.
    session.add_all([
        _payment("pay-b-newest", BASE_TIME + timedelta(minutes=10)),
        _payment("pay-c-middle", BASE_TIME + timedelta(minutes=5)),
        _payment("pay-a-oldest", BASE_TIME),
    ])
    session.commit()

    result = _format_order(_reload_order(session))
    assert result["payment"]["id"] == "pay-b-newest"


def test_payment_tie_broken_by_id(session):
    session.add_all([
        _payment("pay-z", BASE_TIME),
        _payment("pay-m", BASE_TIME),
        _payment("pay-a", BASE_TIME),
    ])
    session.commit()

    order = _reload_order(session)
    first = _format_order(order)["payment"]["id"]
    # Also verify independence from in-memory collection order.
    order.payments.reverse()
    second = _format_order(order)["payment"]["id"]
    assert first == second == "pay-z"


# --------------------------------------------------------------------------- #
# 3-4. Shipment selection
# --------------------------------------------------------------------------- #

def test_latest_shipment_selected_by_created_at(session):
    session.add_all([
        _shipment("shp-b-newest", BASE_TIME + timedelta(hours=2)),
        _shipment("shp-a-oldest", BASE_TIME),
        _shipment("shp-c-middle", BASE_TIME + timedelta(hours=1)),
    ])
    session.commit()

    result = _format_order(_reload_order(session))
    assert result["shipment"]["id"] == "shp-b-newest"
    assert result["shipment"]["tracking_number"] == "FE-shp-b-newest"


def test_shipment_tie_broken_by_id(session):
    session.add_all([
        _shipment("shp-y", BASE_TIME),
        _shipment("shp-b", BASE_TIME),
    ])
    session.commit()

    order = _reload_order(session)
    first = _format_order(order)["shipment"]["id"]
    order.shipments.reverse()
    second = _format_order(order)["shipment"]["id"]
    assert first == second == "shp-y"


def test_selection_handles_mixed_naive_and_aware_timestamps():
    """Naive datetimes (as returned by SQLite) are compared as UTC."""
    order = Order(id="ord-mix", user_id="u", status="PENDING_PAYMENT",
                  total_amount=Decimal("1.00"),
                  created_at=BASE_TIME, updated_at=BASE_TIME)
    order.payments.extend([
        Payment(id="p-aware", order_id="ord-mix", slip_reference="s",
                slip_status="UPLOADED", verification_status="UNAVAILABLE",
                created_at=BASE_TIME),
        Payment(id="p-naive-newer", order_id="ord-mix", slip_reference="s",
                slip_status="UPLOADED", verification_status="UNAVAILABLE",
                created_at=(BASE_TIME + timedelta(seconds=1)).replace(tzinfo=None)),
    ])
    assert _format_order(order)["payment"]["id"] == "p-naive-newer"


# --------------------------------------------------------------------------- #
# 5-6. Contract: None when empty, single object (not array)
# --------------------------------------------------------------------------- #

def test_order_without_payment_or_shipment_returns_none(client, auth_headers):
    resp = client.get("/api/orders/ord-sel", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment"] is None
    assert body["shipment"] is None


def test_api_returns_single_latest_objects_not_arrays(client, session, auth_headers):
    session.add_all([
        _payment("pay-new", BASE_TIME + timedelta(minutes=1)),
        _payment("pay-old", BASE_TIME),
        _shipment("shp-new", BASE_TIME + timedelta(minutes=1)),
        _shipment("shp-old", BASE_TIME),
    ])
    session.commit()

    for url in ("/api/orders/ord-sel", "/api/orders/my-orders"):
        resp = client.get(url, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        order = body if isinstance(body, dict) else body[0]
        assert isinstance(order["payment"], dict)
        assert isinstance(order["shipment"], dict)
        assert order["payment"]["id"] == "pay-new"
        assert order["shipment"]["id"] == "shp-new"
        # Shipment response keys unchanged (no new fields added to the contract).
        assert set(order["shipment"].keys()) == {
            "id", "order_id", "carrier_name", "tracking_number",
            "status", "estimated_delivery",
        }


def test_order_response_schema_fields_are_single_objects():
    fields = OrderResponse.model_fields
    for name in ("payment", "shipment"):
        annotation = str(fields[name].annotation)
        assert "List" not in annotation and "list" not in annotation
        assert fields[name].default is None


# --------------------------------------------------------------------------- #
# 7. Model / mapper checks
# --------------------------------------------------------------------------- #

def test_configure_mappers_succeeds():
    configure_mappers()


def test_shipment_created_at_column_definition():
    col = class_mapper(Shipment).columns["created_at"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True
    assert col.nullable is False
    assert col.default is not None
    arg = getattr(col.default, "arg", None)
    assert arg is not None
    value = arg(None) if callable(arg) else arg
    assert isinstance(value, datetime)
    assert value.utcoffset() == timedelta(0)


# --------------------------------------------------------------------------- #
# 8. Migration checks (static; Alembic is NOT executed)
# --------------------------------------------------------------------------- #

def _module_assignments(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    values = {}
    for node in tree.body:
        target = None
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target:
            values[target] = ast.literal_eval(value) if value is not None else None
    return values


def _function_source(path, name) -> str:
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise AssertionError(f"{name} not found in {path}")



def test_revision_chain_is_linear():
    revisions = {}
    for fname in os.listdir(VERSIONS_DIR):
        if fname.endswith(".py"):
            meta = _module_assignments(os.path.join(VERSIONS_DIR, fname))
            revisions[meta["revision"]] = meta["down_revision"]

    assert revisions == {
        "d6931d9c9757": None,
        "7b2e4c1a9f30": "d6931d9c9757",
        "c3a8e1b2f904": "7b2e4c1a9f30",
        "e4f1a2b3c5d6": "c3a8e1b2f904",
        "f5a2b3c4d5e6": "e4f1a2b3c5d6",
    }
    heads = set(revisions) - {d for d in revisions.values() if d}
    assert heads == {"f5a2b3c4d5e6"}


def _parse_migration_ast(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    meta = {}
    upgrade_add_columns = []
    downgrade_drop_columns = []

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = (
                node.target.id
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                else (
                    node.targets[0].id
                    if isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Name)
                    else None
                )
            )
            if target:
                meta[target] = (
                    ast.literal_eval(node.value) if node.value is not None else None
                )
        elif isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            for sub in node.body:
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    call = sub.value
                    if (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == "add_column"
                    ):
                        table = ast.literal_eval(call.args[0])
                        col_call = call.args[1]
                        assert isinstance(col_call, ast.Call)
                        col_name = ast.literal_eval(col_call.args[0])
                        type_call = col_call.args[1]
                        assert isinstance(type_call, ast.Call)
                        assert isinstance(type_call.func, ast.Attribute)
                        type_name = type_call.func.attr
                        length = None
                        if type_call.args:
                            length = ast.literal_eval(type_call.args[0])
                        elif type_call.keywords:
                            for kw in type_call.keywords:
                                if kw.arg == "length":
                                    length = ast.literal_eval(kw.value)
                        nullable = None
                        for kw in col_call.keywords:
                            if kw.arg == "nullable":
                                nullable = ast.literal_eval(kw.value)
                        upgrade_add_columns.append(
                            {
                                "table": table,
                                "column": col_name,
                                "type": type_name,
                                "length": length,
                                "nullable": nullable,
                            }
                        )
        elif isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            for sub in node.body:
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    call = sub.value
                    if (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == "drop_column"
                    ):
                        table = ast.literal_eval(call.args[0])
                        col_name = ast.literal_eval(call.args[1])
                        downgrade_drop_columns.append((table, col_name))

    return meta, upgrade_add_columns, downgrade_drop_columns


def test_profile_and_media_migration_upgrade_and_downgrade_are_consistent():
    meta, added_columns, dropped_columns = _parse_migration_ast(PROFILE_MEDIA_MIGRATION)

    # 1. Revision identifiers
    assert meta["revision"] == "c3a8e1b2f904"
    assert meta["down_revision"] == "7b2e4c1a9f30"
    assert meta.get("branch_labels") is None
    assert meta.get("depends_on") is None

    # 2. Upgrade: 4 safe nullable columns without destructive statements or backfills
    assert added_columns == [
        {
            "table": "users",
            "column": "name",
            "type": "String",
            "length": 255,
            "nullable": True,
        },
        {
            "table": "users",
            "column": "store_name",
            "type": "String",
            "length": 255,
            "nullable": True,
        },
        {
            "table": "products",
            "column": "image_url",
            "type": "String",
            "length": 1024,
            "nullable": True,
        },
        {
            "table": "products",
            "column": "color",
            "type": "String",
            "length": 50,
            "nullable": True,
        },
    ]

    # 3. Downgrade: clean reversal of added columns
    assert dropped_columns == [
        ("products", "color"),
        ("products", "image_url"),
        ("users", "store_name"),
        ("users", "name"),
    ]


def test_shipment_migration_upgrade_and_downgrade_are_consistent():
    upgrade = _function_source(SHIPMENT_MIGRATION, "upgrade")
    downgrade = _function_source(SHIPMENT_MIGRATION, "downgrade")

    # Upgrade: add nullable -> backfill existing rows -> enforce NOT NULL.
    add_idx = upgrade.index("op.add_column")
    fill_idx = upgrade.index("UPDATE shipments SET created_at")
    alter_idx = upgrade.index("op.alter_column")
    assert add_idx < fill_idx < alter_idx
    assert "sa.DateTime(timezone=True)" in upgrade
    assert "nullable=True" in upgrade[add_idx:fill_idx]
    assert "nullable=False" in upgrade[alter_idx:]

    assert "op.drop_column('shipments', 'created_at')" in downgrade


def test_initial_migration_unchanged_for_shipments():
    upgrade = _function_source(INITIAL_MIGRATION, "upgrade")
    start = upgrade.index("op.create_table('shipments'")
    end = upgrade.index("op.create_index(op.f('ix_shipments_order_id')")
    shipments_block = upgrade[start:end]
    assert "created_at" not in shipments_block
    assert _module_assignments(INITIAL_MIGRATION)["down_revision"] is None
