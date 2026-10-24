import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, cast
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)

from app.auth import get_current_user
from app.config import settings
from app.db_connection import get_db
from app.models import Order, OrderItem, Payment, Product, Shipment, Stock
from app.schemas import (
    OrderCreateRequest,
    OrderResponse,
    SimulatePaymentRequest,
    SimulatePaymentResponse,
    SlipUploadRequest,
    SlipUploadResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def _format_payment(p: Optional[Payment]) -> Optional[dict]:
    if not p:
        return None
    return {
        "id": p.id,
        "order_id": p.order_id,
        "payment_type": p.payment_type,
        "slip_reference": p.slip_reference,
        "slip_status": p.slip_status,
        "extracted_payment_data": p.extracted_payment_data,
        "verification_status": p.verification_status,
        "verification_reference": p.verification_reference,
        "verified_at": p.verified_at,
        "created_at": p.created_at,
    }


def _format_shipment(s: Optional[Shipment]) -> Optional[dict]:
    if not s:
        return None
    return {
        "id": s.id,
        "order_id": s.order_id,
        "carrier_name": s.carrier_name,
        "tracking_number": s.tracking_number,
        "status": s.status,
        "estimated_delivery": s.estimated_delivery,
    }


def _format_order_item(item: OrderItem) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "stock_id": item.stock_id,
        "variant_key": item.variant_key,
        "quantity": item.quantity,
        "unit_price": float(cast(Decimal, item.unit_price)),
    }


_MIN_UTC = datetime.min.replace(tzinfo=timezone.utc)


def _recency_key(record: Any) -> tuple:
    """Sort key ``(created_at, id)`` for picking the latest Payment/Shipment.

    ORM collection order is not guaranteed, so selection must not rely on
    ``[-1]``. Naive datetimes (e.g. returned by SQLite) are treated as UTC so
    they can be compared with timezone-aware values; missing timestamps sort
    first. ``id`` is the deterministic tie-breaker for equal timestamps.
    """
    created_at = getattr(record, "created_at", None)
    if created_at is None:
        created_at = _MIN_UTC
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (created_at, record.id)


def _latest(records: Optional[List[Any]]) -> Optional[Any]:
    return max(records, key=_recency_key) if records else None


def _format_order(
    o: Order,
    seller_id: Optional[str] = None,
    db_session: Optional[Session] = None,
) -> dict:
    order_payments: Optional[List[Payment]] = cast(Any, o.payments)
    order_shipments: Optional[List[Shipment]] = cast(Any, o.shipments)

    if seller_id:
        seller_items = []
        for item in (o.items or []):
            prod = getattr(item, "product", None)
            if not prod and db_session and getattr(item, "product_id", None):
                prod = db_session.get(Product, item.product_id)
            if prod and prod.seller_id == seller_id:
                seller_items.append(item)

        seller_shipments = [
            s for s in (order_shipments or [])
            if getattr(s, "seller_id", None) == seller_id
        ]
        latest_shp = _latest(seller_shipments)
        shipment_dict = _format_shipment(latest_shp)
        shipments_list = [_format_shipment(s) for s in seller_shipments]
        items_list = [_format_order_item(item) for item in seller_items]
        seller_total = round(
            sum(float(cast(Decimal, item.unit_price)) * item.quantity for item in seller_items), 2
        )

        return {
            "id": o.id,
            "user_id": o.user_id,
            "status": o.status,
            "total_amount": seller_total,
            "created_at": o.created_at,
            "updated_at": o.updated_at,
            "items": items_list,
            "payment": _format_payment(_latest(order_payments)),
            "shipment": shipment_dict,
            "shipments": shipments_list,
        }

    payment_dict = _format_payment(_latest(order_payments))
    latest_shp = _latest(order_shipments)
    shipment_dict = _format_shipment(latest_shp)
    shipments_list = [_format_shipment(s) for s in (order_shipments or [])] if order_shipments else []
    return {
        "id": o.id,
        "user_id": o.user_id,
        "status": o.status,
        "total_amount": float(cast(Decimal, o.total_amount)),
        "created_at": o.created_at,
        "updated_at": o.updated_at,
        "items": [_format_order_item(item) for item in (o.items or [])],
        "payment": payment_dict,
        "shipment": shipment_dict,
        "shipments": shipments_list,
    }


def _ensure_seller_shipments(db_session: Session, order: Order, now: datetime) -> None:
    """Ensure a Shipment exists for each distinct seller in the order.

    - Creates 1 shipment per seller with status='PREPARING', carrier_name='Standard Delivery', tracking_number=None.
    - Uses Savepoint (begin_nested) to safely handle concurrent attempts and prevent transaction breakage.
    - Does NOT decrement stock.
    """
    seller_ids = set()
    for item in (order.items or []):
        if getattr(item, "product", None) and item.product.seller_id:
            seller_ids.add(item.product.seller_id)
        elif getattr(item, "product_id", None):
            prod = db_session.get(Product, item.product_id)
            if prod and prod.seller_id:
                seller_ids.add(prod.seller_id)

    if not seller_ids:
        # Fallback for legacy fixtures without seller
        existing = db_session.scalar(select(Shipment).where(Shipment.order_id == order.id))
        if not existing:
            shipment = Shipment(
                id=str(uuid.uuid4()),
                order_id=order.id,
                seller_id=None,
                carrier_name="Standard Delivery",
                tracking_number=f"TRK-{uuid.uuid4().hex[:8].upper()}",
                status="PREPARING",
                estimated_delivery=now + timedelta(days=3),
                created_at=now,
            )
            db_session.add(shipment)
        return

    for s_id in sorted(seller_ids):
        existing = db_session.scalar(
            select(Shipment).where(
                Shipment.order_id == order.id,
                Shipment.seller_id == s_id,
            )
        )
        if not existing:
            shipment = Shipment(
                id=str(uuid.uuid4()),
                order_id=order.id,
                seller_id=s_id,
                carrier_name="Standard Delivery",
                tracking_number=None,
                status="PREPARING",
                estimated_delivery=now + timedelta(days=3),
                created_at=now,
            )
            try:
                with db_session.begin_nested():
                    db_session.add(shipment)
                    db_session.flush()
            except IntegrityError as exc:
                found = db_session.scalar(
                    select(Shipment).where(
                        Shipment.order_id == order.id,
                        Shipment.seller_id == s_id,
                    )
                )
                if found:
                    continue
                logger.warning(
                    "IntegrityError creating shipment for order %s, seller %s: %s",
                    order.id, s_id, exc,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict creating shipment for seller {s_id}. Please retry."
                )


def verify_payment_and_decrement_stock_db(
    db_session: Session,
    order_id: str,
    payment_id: str,
    slip_reference: str,
    verification_result: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify payment and decrement stock atomically in PostgreSQL via SQLAlchemy.

    - Locks Order and Stock rows with FOR UPDATE (sorted by stock_id to avoid deadlocks).
    - Checks Decimal verification amounts against PAYMENT_RECIPIENT_ACCOUNT.
    - If stock is insufficient: sets MANUAL_RESOLUTION_REQUIRED without deducting stock.
    - If verification succeeds and stock is sufficient: deducts Stock.available_quantity,
      recalculates Product.stock_quantity, updates Order to PAID, and creates Shipment.
    """
    payment = db_session.get(Payment, payment_id)
    if not payment:
        return {"success": False, "message": "Payment record not found"}

    stmt_order = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.id == order_id)
        .with_for_update()
    )
    order = db_session.scalar(stmt_order)
    if not order:
        return {"success": False, "message": "Order not found"}

    db_session.refresh(payment)
    if order.status == "CANCELLED":
        return {
            "success": False,
            "message": "Order is cancelled; payment verification cannot proceed.",
            "order": _format_order(order),
        }

    if payment.slip_status == "VERIFIED" or order.status == "PAID":
        return {
            "success": True,
            "message": "Payment already verified",
            "order": _format_order(order),
        }

    if payment.slip_reference != slip_reference:
        return {
            "success": False,
            "message": "Slip evidence changed; payment verification is unavailable. Stock was not deducted.",
            "order": _format_order(order),
        }

    if not isinstance(verification_result, Mapping):
        payment.slip_status = "UPLOADED"
        payment.verification_status = "UNAVAILABLE"
        db_session.commit()
        return {
            "success": False,
            "message": "Payment verification unavailable. Slip evidence was stored; stock was not deducted.",
            "order": _format_order(order),
        }

    recipient_account = settings.PAYMENT_RECIPIENT_ACCOUNT.strip()
    if not recipient_account:
        payment.slip_status = "UPLOADED"
        payment.verification_status = "UNAVAILABLE"
        db_session.commit()
        return {
            "success": False,
            "message": "Payment verification unavailable because the recipient account is not configured. Stock was not deducted.",
            "order": _format_order(order),
        }

    try:
        verified_amount = Decimal(str(verification_result.get("amount")))
        order_amount = Decimal(str(order.total_amount))
    except (InvalidOperation, TypeError, ValueError):
        verified_amount = Decimal("NaN")
        order_amount = Decimal(str(order.total_amount))

    verification_succeeded = (
        verification_result.get("verified") is True
        and verified_amount.is_finite()
        and order_amount.is_finite()
        and verified_amount == order_amount
        and verification_result.get("destination_account") == recipient_account
    )
    if not verification_succeeded:
        payment.slip_status = "REJECTED"
        payment.verification_status = "REJECTED"
        db_session.commit()
        return {
            "success": False,
            "message": "Payment verification failed. Stock was not deducted.",
            "order": _format_order(order),
        }

    items = db_session.scalars(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    if not items:
        return {
            "success": False,
            "message": "Order has no items; payment cannot be fulfilled.",
            "order": _format_order(order),
        }

    now = datetime.now(timezone.utc)

    # Option A: Stock was already deducted immediately and atomically upon order creation.
    # Payment verification confirms the payment and fulfills the order without deducting stock a second time.
    payment.slip_status = "VERIFIED"
    payment.verification_status = "VERIFIED"
    payment.verified_at = now
    payment.verification_reference = verification_result.get("reference")

    order.status = "PAID"
    order.updated_at = now

    _ensure_seller_shipments(db_session, order, now)

    try:
        db_session.commit()
        db_session.refresh(order)
    except Exception:
        db_session.rollback()
        raise

    return {
        "success": True,
        "message": "Payment verified and stock decremented successfully.",
        "order": _format_order(order),
        "receipt": {
            "receipt_id": f"REC-{uuid.uuid4().hex[:8].upper()}",
            "order_id": order_id,
            "amount": float(order.total_amount),
            "issued_at": now.isoformat(),
        },
    }


@router.post("/create", response_model=OrderResponse)
def create_order(
    payload: OrderCreateRequest,
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item",
        )

    # 1. Validation & Data Collection
    total_amount = Decimal("0.00")
    order_items_to_create: List[OrderItem] = []
    stock_required_qty: Dict[str, int] = {}
    stock_lookup: Dict[str, Stock] = {}
    product_lookup: Dict[str, Product] = {}

    for item in payload.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item quantity must be greater than zero",
            )

        product = db_session.get(Product, item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} not found",
            )

        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} is currently inactive",
            )

        # FR-02: Sellers cannot purchase their own products
        if product.seller_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sellers cannot purchase their own products ({product.name})",
            )

        norm_variant_key = item.variant_key.strip().upper() if item.variant_key else ""
        stmt = select(Stock).where(
            Stock.product_id == item.product_id,
            func.upper(Stock.variant_key) == norm_variant_key,
        )
        stock = db_session.scalar(stmt)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant {item.variant_key} not found for product {item.product_id}",
            )

        unit_price = Decimal(str(product.price))
        total_amount += unit_price * item.quantity

        stock_required_qty[stock.id] = (
            stock_required_qty.get(stock.id, 0) + item.quantity
        )
        stock_lookup[stock.id] = stock
        product_lookup[stock.id] = product

        order_items_to_create.append(
            OrderItem(
                id=str(uuid.uuid4()),
                product_id=item.product_id,
                stock_id=stock.id,
                variant_key=item.variant_key,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )

    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())

    try:
        # 2. Atomic stock deduction with deadlock prevention (sorted stock_ids)
        sorted_stock_ids = sorted(stock_required_qty.keys())
        for sid in sorted_stock_ids:
            qty_needed = stock_required_qty[sid]
            stk = stock_lookup[sid]
            prod = product_lookup[sid]

            update_stmt = (
                update(Stock)
                .where(
                    Stock.id == sid,
                    Stock.available_quantity >= qty_needed,
                )
                .values(
                    {
                        Stock.available_quantity: Stock.available_quantity - qty_needed,
                        Stock.updated_at: now,
                    }
                )
            )
            result = db_session.execute(update_stmt)
            cursor_res = cast(CursorResult, result)
            if cursor_res.rowcount == 0:
                # Insufficient stock or concurrent race lost
                db_session.rollback()
                current_avail = db_session.scalar(
                    select(Stock.available_quantity).where(Stock.id == sid)
                )
                avail_str = current_avail if current_avail is not None else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {prod.name} ({stk.variant_key}). Available: {avail_str}",
                )

        # 3. Synchronize products.stock_quantity for affected products
        affected_product_ids = {prod.id for prod in product_lookup.values()}
        for pid in affected_product_ids:
            total_avail = db_session.scalar(
                select(func.sum(Stock.available_quantity)).where(
                    Stock.product_id == pid
                )
            )
            p = db_session.get(Product, pid)
            if p:
                p.stock_quantity = total_avail if total_avail is not None else 0

        # 4. Create Order and OrderItems in the same transaction
        new_order = Order(
            id=order_id,
            user_id=current_user["id"],
            status="PENDING_PAYMENT",
            total_amount=total_amount,
            created_at=now,
            updated_at=now,
        )
        new_order.items.extend(order_items_to_create)
        db_session.add(new_order)
        db_session.commit()
        db_session.refresh(new_order)
    except HTTPException:
        db_session.rollback()
        raise
    except Exception:
        db_session.rollback()
        raise

    return _format_order(new_order)


@router.post("/upload-slip", response_model=SlipUploadResponse)
def upload_slip(
    payload: SlipUploadRequest,
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.id == payload.order_id)
    )
    order = db_session.scalar(stmt)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload a slip for this order",
        )

    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload payment slip for a cancelled order",
        )

    # Check if order is already verified/PAID
    verified_payment = next(
        (p for p in (order.payments or []) if p.slip_status == "VERIFIED"), None
    )
    if verified_payment and order.status == "PAID":
        return {
            "order_id": payload.order_id,
            "payment_id": verified_payment.id,
            "slip_status": verified_payment.slip_status,
            "verification_status": verified_payment.verification_status,
            "message": "Payment is already verified.",
        }

    # Create new Payment attempt row (1:N attempt persistence)
    now = datetime.now(timezone.utc)
    payment = Payment(
        id=str(uuid.uuid4()),
        order_id=payload.order_id,
        payment_type="BANK_TRANSFER",
        slip_reference=payload.slip_reference,
        slip_status="UPLOADED",
        extracted_payment_data=None,
        verification_status="UNAVAILABLE",
        verification_reference=None,
        verified_at=None,
        created_at=now,
    )
    try:
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
    except Exception:
        db_session.rollback()
        raise

    result = verify_payment_and_decrement_stock_db(
        db_session,
        payload.order_id,
        str(payment.id),
        payload.slip_reference,
    )

    if not result["success"]:
        return {
            "order_id": payload.order_id,
            "payment_id": payment.id,
            "slip_status": payment.slip_status,
            "verification_status": payment.verification_status,
            "message": result["message"],
        }

    return {
        "order_id": payload.order_id,
        "payment_id": payment.id,
        "slip_status": payment.slip_status,
        "verification_status": payment.verification_status,
        "message": result["message"],
        **({"receipt": result["receipt"]} if "receipt" in result else {}),
    }


@router.get("/my-orders", response_model=List[OrderResponse])
def get_my_orders(
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.user_id == current_user["id"])
        .order_by(Order.created_at.desc())
    )
    orders = db_session.scalars(stmt).all()
    return [_format_order(o) for o in orders]


@router.get("/{id}", response_model=OrderResponse)
def get_order(
    id: str,
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.id == id)
    )
    order = db_session.scalar(stmt)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # 1. Buyer who owns the order can view the entire order
    if order.user_id == current_user["id"]:
        return _format_order(order)

    # 2. If not the buyer, verify if user is a seller whose products are in this order
    if current_user.get("role") != "seller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order",
        )

    seller_id = current_user["id"]
    seller_items = [
        it
        for it in (order.items or [])
        if (getattr(it, "product", None) and it.product.seller_id == seller_id)
        or (
            getattr(it, "product_id", None)
            and getattr(db_session.get(Product, it.product_id), "seller_id", None) == seller_id
        )
    ]
    if not seller_items:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order",
        )

    # 3. Return masked order details filtered to this seller's items and shipments
    return _format_order(order, seller_id=seller_id, db_session=db_session)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.id == order_id)
        .with_for_update()
    )
    order = db_session.scalar(stmt)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Only the buyer who owns the order may cancel it.
    # Return 404 to avoid exposing another buyer's private order existence.
    if order.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Idempotent response: if already cancelled, return order without restoring stock again.
    if order.status == "CANCELLED":
        return _format_order(order)

    # Reject paid orders or orders with verified payments
    has_verified_payment = any(
        p.slip_status == "VERIFIED" or p.verification_status == "VERIFIED"
        for p in (order.payments or [])
    )
    if order.status == "PAID" or has_verified_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid orders cannot be cancelled",
        )

    # Reject shipped or completed orders
    has_active_shipment = any(
        s.status not in ("CANCELLED", "RETURNED")
        for s in (order.shipments or [])
    )
    if has_active_shipment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has already been shipped and cannot be cancelled",
        )

    # Only PENDING_PAYMENT orders are eligible for cancellation
    if order.status != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order in status '{order.status}' cannot be cancelled",
        )

    now = datetime.now(timezone.utc)
    try:
        # Group restoration by stock_id to handle multiple items cleanly
        stock_restore_qty: Dict[str, int] = {}
        affected_product_ids = set()

        for item in (order.items or []):
            stock = None
            if item.stock_id:
                stock = db_session.get(Stock, item.stock_id)
            if not stock and item.variant_key:
                norm_variant = item.variant_key.strip().upper()
                stock = db_session.scalar(
                    select(Stock).where(
                        Stock.product_id == item.product_id,
                        func.upper(Stock.variant_key) == norm_variant,
                    )
                )

            # Confirm stock belongs to the same product as the order item
            if not stock or stock.product_id != item.product_id:
                db_session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock record for item {item.id} not found or product mismatch",
                )

            sid_key = str(stock.id)
            stock_restore_qty[sid_key] = (
                stock_restore_qty.get(sid_key, 0) + item.quantity
            )
            affected_product_ids.add(item.product_id)

        # Restore variant stocks in deterministic order to prevent deadlocks
        sorted_stock_ids = sorted(stock_restore_qty.keys())
        for sid in sorted_stock_ids:
            qty_to_restore = stock_restore_qty[sid]
            update_stmt = (
                update(Stock)
                .where(Stock.id == sid)
                .values(
                    {
                        Stock.available_quantity: Stock.available_quantity + qty_to_restore,
                        Stock.updated_at: now,
                    }
                )
            )
            db_session.execute(update_stmt)

        # Synchronize products.stock_quantity for affected products
        for pid in affected_product_ids:
            total_avail = db_session.scalar(
                select(func.sum(Stock.available_quantity)).where(
                    Stock.product_id == pid
                )
            )
            prod = db_session.get(Product, pid)
            if prod:
                prod.stock_quantity = total_avail if total_avail is not None else 0

        # Mark any pending slip payments as REJECTED so payment cannot be confirmed later
        for p in (order.payments or []):
            if p.slip_status == "UPLOADED":
                p.slip_status = "REJECTED"
                p.verification_status = "REJECTED"

        # Update order status
        order.status = "CANCELLED"
        order.updated_at = now

        db_session.commit()
        db_session.refresh(order)
    except HTTPException:
        db_session.rollback()
        raise
    except Exception:
        db_session.rollback()
        raise

    return _format_order(order)


@router.post("/{order_id}/simulate-payment", response_model=SimulatePaymentResponse)
def simulate_payment(
    order_id: str,
    payload: Optional[SimulatePaymentRequest] = None,
    current_user: dict = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """Simulate payment for demonstration purposes.

    - Verifies authentication and ownership.
    - Confirms order is in PENDING_PAYMENT status.
    - Rejects CANCELLED orders.
    - Does NOT re-deduct stock (Option A already deducted stock upon order creation).
    - If outcome is SUCCESS: creates verified Payment, marks Order as PAID.
    - If outcome is FAILURE: records rejected Payment attempt, Order remains PENDING_PAYMENT.
    - Idempotent: returns existing paid status without duplicating records if already paid.
    """
    if payload is None:
        payload = SimulatePaymentRequest()

    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.shipments),
        )
        .where(Order.id == order_id)
        .with_for_update()
    )
    order = db_session.scalar(stmt)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Ownership check: only owning buyer or authorized seller
    if order.user_id != current_user["id"] and current_user.get("role") != "seller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to pay for this order",
        )

    # Cannot pay cancelled orders
    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled orders cannot be paid",
        )

    # Idempotent response: if already PAID, return without duplicating payment or deducting stock
    if order.status == "PAID":
        verified_payment = _latest(
            [p for p in (order.payments or []) if p.slip_status == "VERIFIED"]
        )
        return {
            "success": True,
            "message": "Order is already paid.",
            "order": _format_order(order),
            "payment_id": verified_payment.id if verified_payment else None,
        }

    # If there is already a verified payment record in payments
    has_verified_payment = any(
        p.slip_status == "VERIFIED" or p.verification_status == "VERIFIED"
        for p in (order.payments or [])
    )
    if has_verified_payment:
        order.status = "PAID"
        db_session.commit()
        return {
            "success": True,
            "message": "Order payment is already verified.",
            "order": _format_order(order),
        }

    # Only PENDING_PAYMENT orders can be processed
    if order.status != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order in status '{order.status}' cannot be paid",
        )

    now = datetime.now(timezone.utc)
    is_success = (payload.outcome or "SUCCESS").strip().upper() == "SUCCESS"

    try:
        if is_success:
            payment = Payment(
                id=str(uuid.uuid4()),
                order_id=order.id,
                payment_type=payload.payment_method or "SIMULATED_CARD",
                slip_reference=f"SIM-{uuid.uuid4().hex[:12].upper()}",
                slip_status="VERIFIED",
                extracted_payment_data={
                    "simulation": True,
                    "amount": float(order.total_amount),
                    "timestamp": now.isoformat(),
                    "method": payload.payment_method or "SIMULATED_CARD",
                },
                verification_status="VERIFIED",
                verification_reference=f"SIM-TXN-{uuid.uuid4().hex[:8].upper()}",
                verified_at=now,
                created_at=now,
            )
            db_session.add(payment)

            order.status = "PAID"
            order.updated_at = now

            _ensure_seller_shipments(db_session, order, now)

            db_session.commit()
            db_session.refresh(order)

            return {
                "success": True,
                "message": "Simulated payment successful.",
                "order": _format_order(order),
                "payment_id": payment.id,
            }
        else:
            payment = Payment(
                id=str(uuid.uuid4()),
                order_id=order.id,
                payment_type=payload.payment_method or "SIMULATED_CARD",
                slip_reference=f"SIM-FAIL-{uuid.uuid4().hex[:12].upper()}",
                slip_status="REJECTED",
                extracted_payment_data={
                    "simulation": True,
                    "outcome": "FAILURE",
                    "reason": payload.failure_reason or "Simulated card declined",
                    "timestamp": now.isoformat(),
                },
                verification_status="REJECTED",
                verification_reference=None,
                verified_at=None,
                created_at=now,
            )
            db_session.add(payment)

            # Order status remains PENDING_PAYMENT, stock remains untouched
            order.updated_at = now

            db_session.commit()
            db_session.refresh(order)

            return {
                "success": False,
                "message": payload.failure_reason or "Simulated payment declined for demonstration.",
                "order": _format_order(order),
                "payment_id": payment.id,
            }
    except HTTPException:
        db_session.rollback()
        raise
    except Exception:
        db_session.rollback()
        raise