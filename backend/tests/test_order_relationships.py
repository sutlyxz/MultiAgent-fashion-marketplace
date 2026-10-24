"""Tests for the Order ↔ Payment / Shipment one-to-many (1:N) relationships.

All tests are static/import-only — no database connection is required.
They verify ORM metadata, relationship configuration, column constraints,
default values, mapper configuration, and consistency with Alembic migration.
"""

import ast
from datetime import datetime, timezone
import os
import sys

import pytest
from sqlalchemy import DateTime
from sqlalchemy.orm import configure_mappers, class_mapper


BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.models import Order, Payment, Shipment


def test_order_payments_and_shipments_are_collections():
    """Order.payments and Order.shipments must be 1:N collections (uselist=True)."""
    order_mapper = class_mapper(Order)
    
    payments_rel = order_mapper.relationships["payments"]
    assert payments_rel.uselist is True, "Order.payments must be a collection (uselist=True)"
    
    shipments_rel = order_mapper.relationships["shipments"]
    assert shipments_rel.uselist is True, "Order.shipments must be a collection (uselist=True)"


def test_payment_and_shipment_back_populates():
    """Payment.order and Shipment.order must link back to Order with correct back_populates."""
    payment_mapper = class_mapper(Payment)
    shipment_mapper = class_mapper(Shipment)
    
    payment_order_rel = payment_mapper.relationships["order"]
    assert payment_order_rel.back_populates == "payments"
    assert payment_order_rel.mapper.class_ is Order
    
    shipment_order_rel = shipment_mapper.relationships["order"]
    assert shipment_order_rel.back_populates == "shipments"
    assert shipment_order_rel.mapper.class_ is Order


def test_order_id_not_unique_in_payment_and_shipment():
    """order_id in Payment and Shipment must NOT have unique=True."""
    payment_mapper = class_mapper(Payment)
    shipment_mapper = class_mapper(Shipment)
    
    payment_order_id_col = payment_mapper.columns["order_id"]
    assert not payment_order_id_col.unique, "Payment.order_id must NOT be unique"
    
    shipment_order_id_col = shipment_mapper.columns["order_id"]
    assert not shipment_order_id_col.unique, "Shipment.order_id must NOT be unique"


def test_shipment_tracking_number_is_unique():
    """Shipment.tracking_number must remain unique."""
    shipment_mapper = class_mapper(Shipment)
    tracking_num_col = shipment_mapper.columns["tracking_number"]
    assert tracking_num_col.unique is True, "Shipment.tracking_number must be unique"


def test_payment_created_at_timezone_aware():
    """Payment.created_at must be timezone-aware DateTime, nullable=False, with valid UTC default."""
    payment_mapper = class_mapper(Payment)
    created_at_col = payment_mapper.columns["created_at"]
    
    assert isinstance(created_at_col.type, DateTime)
    assert created_at_col.type.timezone is True, "created_at must be DateTime(timezone=True)"
    assert created_at_col.nullable is False, "created_at must be nullable=False"
    
    payment = Payment(
        order_id="ord-123",
        slip_reference="ref-123",
    )
    # Trigger Python-side default if present
    if created_at_col.default is not None:
        arg = getattr(created_at_col.default, "arg", None)
        assert arg is not None
        val = arg(None) if callable(arg) else arg
        assert isinstance(val, datetime)
        assert val.tzinfo is not None, "created_at default must be timezone-aware UTC"


def test_configure_mappers_succeeds():
    """sqlalchemy.orm.configure_mappers() must pass without relationship warnings or errors."""
    configure_mappers()


def test_model_and_migration_schema_consistency():
    """Initial migration must match updated 1:N models."""
    migration_path = os.path.join(
        BACKEND_DIR, "migrations", "versions", "d6931d9c9757_initial_schema.py"
    )
    assert os.path.exists(migration_path), "Migration file must exist"
    
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "op.create_index(op.f('ix_payments_order_id'), 'payments', ['order_id'], unique=False)" in content
    assert "op.create_index(op.f('ix_shipments_order_id'), 'shipments', ['order_id'], unique=False)" in content
    assert "op.create_index(op.f('ix_shipments_tracking_number'), 'shipments', ['tracking_number'], unique=True)" in content
    assert "sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)" in content
