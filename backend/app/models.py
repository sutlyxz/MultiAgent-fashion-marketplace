"""SQLAlchemy 2.x ORM models for the fashion marketplace.

These models mirror the in-memory collections defined in ``app.database`` and
reuse the shared declarative ``Base`` created in ``app.db_connection`` so that a
single metadata object is populated for migrations.

Persistence is not wired into the API in this step: routers still use the
in-memory ``Database``. Identifiers are preserved as UUID strings (``String(36)``)
to stay compatible with the existing API contracts, and monetary values use
``Numeric`` so they are never stored as floating point.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_connection import Base


def _new_uuid() -> str:
    """Generate identifiers in the same format the API already produces."""
    return str(uuid.uuid4())


class User(Base):
    """Buyers and sellers (``app.database`` ``users`` collection)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Existing roles are "buyer" and "seller"; kept as a string to match the API.
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    store_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_users_store_name_lower",
            func.lower(store_name),
            unique=True,
            postgresql_where=(store_name.isnot(None)),
            sqlite_where=(store_name.isnot(None)),
        ),
    )

    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="seller", foreign_keys="Product.seller_id"
    )
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user"
    )
    checkout_sessions: Mapped[List["CheckoutSession"]] = relationship(
        "CheckoutSession", back_populates="user"
    )
    claims_as_buyer: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="buyer", foreign_keys="Claim.buyer_id"
    )
    claims_as_seller: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="seller", foreign_keys="Claim.seller_id"
    )
    crm_tags: Mapped[List["CRMTag"]] = relationship(
        "CRMTag", back_populates="seller", foreign_keys="CRMTag.seller_id"
    )
    crm_tag_links: Mapped[List["UserCRMTag"]] = relationship(
        "UserCRMTag", back_populates="user"
    )


class Product(Base):
    """Sellable products (``app.database`` ``products`` collection)."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Aggregate display value; Stock.available_quantity remains authoritative.
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    seller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    seller: Mapped["User"] = relationship(
        "User", back_populates="products", foreign_keys=[seller_id]
    )
    stocks: Mapped[List["Stock"]] = relationship(
        "Stock", back_populates="product", cascade="all, delete-orphan"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="product"
    )
    checkout_sessions: Mapped[List["CheckoutSession"]] = relationship(
        "CheckoutSession", back_populates="product"
    )


class Stock(Base):
    """Variant-level inventory (``app.database`` ``stocks`` collection)."""

    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_key", name="uq_stocks_product_variant"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    variant_key: Mapped[str] = mapped_column(String(50), nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="stocks")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="stock"
    )
    checkout_sessions: Mapped[List["CheckoutSession"]] = relationship(
        "CheckoutSession", back_populates="stock"
    )


class CheckoutSession(Base):
    """Fast-link checkout sessions (``app.database`` ``checkout_sessions``)."""

    __tablename__ = "checkout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    stock_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stocks.id"), nullable=False, index=True
    )
    variant_key: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Existing statuses: "OPEN", "EXPIRED".
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    user: Mapped["User"] = relationship("User", back_populates="checkout_sessions")
    product: Mapped["Product"] = relationship(
        "Product", back_populates="checkout_sessions"
    )
    stock: Mapped["Stock"] = relationship("Stock", back_populates="checkout_sessions")


class Order(Base):
    """Customer orders (``app.database`` ``orders`` collection)."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # Existing statuses: "PENDING_PAYMENT", "PAID", "MANUAL_RESOLUTION_REQUIRED".
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING_PAYMENT"
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment", back_populates="order", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="order", cascade="all, delete-orphan"
    )
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Line items within an order (``app.database`` ``order_items``)."""

    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    stock_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stocks.id"), nullable=False, index=True
    )
    variant_key: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    stock: Mapped["Stock"] = relationship("Stock", back_populates="order_items")


class Payment(Base):
    """Payment/slip records per order (``app.database`` ``payments``)."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    # Multiple payment records per order (lookups key off order_id).
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    payment_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="BANK_TRANSFER"
    )
    slip_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    # Existing slip statuses: "UPLOADED", "VERIFIED", "REJECTED".
    slip_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UPLOADED"
    )
    # Free-form verifier payload (stored as JSON, nullable until available).
    extracted_payment_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Existing verification statuses: "UNAVAILABLE", "VERIFIED", "REJECTED".
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNAVAILABLE"
    )
    verification_reference: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship("Order", back_populates="payments")


class Shipment(Base):
    """Shipments per order (``app.database`` ``shipments``)."""

    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("order_id", "seller_id", name="uq_shipments_order_seller"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    # Multiple shipment records per order (lookups key off order_id).
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    seller_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    carrier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    # Existing status: "PREPARING" (broader values checked in app logic).
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PREPARING")
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship("Order", back_populates="shipments")
    seller: Mapped["User"] = relationship("User")


class SupportTicket(Base):
    """Support tickets (``app.database`` ``support_tickets``)."""

    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # Existing type: "LOGISTICS_ANOMALY".
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Existing status: "OPEN".
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="support_tickets")
    user: Mapped["User"] = relationship("User", back_populates="support_tickets")


class Claim(Base):
    """Buyer claims against an order (``app.database`` ``claims``)."""

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    buyer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    seller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # Existing statuses: "PENDING", "APPROVED", "REJECTED".
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="claims")
    buyer: Mapped["User"] = relationship(
        "User", back_populates="claims_as_buyer", foreign_keys=[buyer_id]
    )
    seller: Mapped["User"] = relationship(
        "User", back_populates="claims_as_seller", foreign_keys=[seller_id]
    )


class CRMTag(Base):
    """Seller-owned CRM tags (``app.database`` ``crm_tags``)."""

    __tablename__ = "crm_tags"
    __table_args__ = (
        UniqueConstraint("seller_id", "name", name="uq_crm_tags_seller_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    seller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    seller: Mapped["User"] = relationship(
        "User", back_populates="crm_tags", foreign_keys=[seller_id]
    )
    user_associations: Mapped[List["UserCRMTag"]] = relationship(
        "UserCRMTag", back_populates="tag", cascade="all, delete-orphan"
    )


class UserCRMTag(Base):
    """Association between users and CRM tags (``app.database`` ``user_crm_tags``)."""

    __tablename__ = "user_crm_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "tag_id", name="uq_user_crm_tags_user_tag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    tag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("crm_tags.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="crm_tag_links")
    tag: Mapped["CRMTag"] = relationship("CRMTag", back_populates="user_associations")
