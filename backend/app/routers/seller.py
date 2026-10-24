"""Seller operations: claim review and CRM tags (PostgreSQL via SQLAlchemy).

Phase E: these endpoints no longer read or write the in-memory ``db``.
Request/response schemas, status codes and error messages are unchanged.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, cast
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import _format_user, get_current_seller, get_current_user
from app.db_connection import get_db
from app.models import Claim, CRMTag, Order, OrderItem, Product, Shipment, User, UserCRMTag
from app.schemas import (
    BecomeSellerRequest,
    ClaimDecisionRequest,
    ClaimResponse,
    CRMTagCreateRequest,
    CRMTagResponse,
    SellerOrderItemResponse,
    SellerOrderResponse,
    SellerShipmentUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/seller", tags=["Seller Operations"])


@router.post("/become-seller", response_model=UserResponse)
def become_seller(
    payload: BecomeSellerRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable a single user account to open an active boutique atelier without admin approval."""
    user = db.get(User, current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "seller" or (user.store_name and user.store_name.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a registered seller with an active store",
        )

    clean_store_name = payload.store_name.strip()
    if len(clean_store_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store name must be at least 2 characters",
        )

    # Check for duplicate store name (case-insensitive across all users)
    existing_store = db.scalar(
        select(User).where(
            func.lower(User.store_name) == clean_store_name.lower(),
            User.id != user.id,
        )
    )
    if existing_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store name already taken",
        )

    user.role = "seller"
    user.store_name = clean_store_name
    user.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store name already taken",
        )

    # Sync in-memory if present
    try:
        from app.database import db as mem_db
        for mem_u in mem_db.users:
            if mem_u.get("id") == user.id:
                mem_u["role"] = "seller"
                mem_u["store_name"] = clean_store_name
                mem_u["updated_at"] = user.updated_at
    except Exception:
        pass

    return _format_user(user)


def format_claim(claim: Claim) -> Dict[str, Any]:
    return {
        "id": claim.id,
        "order_id": claim.order_id,
        "buyer_id": claim.buyer_id,
        "seller_id": claim.seller_id,
        "reason": claim.reason,
        "status": claim.status,
        "submitted_at": claim.submitted_at,
        "reviewed_at": claim.reviewed_at,
        "ai_recommendation": claim.ai_recommendation,
    }


def _format_tag(tag: CRMTag) -> Dict[str, Any]:
    return {
        "id": tag.id,
        "seller_id": tag.seller_id,
        "name": tag.name,
        "created_at": tag.created_at,
    }


@router.get("/pending-claims", response_model=List[ClaimResponse])
def list_pending_claims(
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    claims = db.scalars(
        select(Claim)
        .where(Claim.seller_id == current_seller["id"], Claim.status == "PENDING")
        .order_by(Claim.submitted_at, Claim.id)
    ).all()
    return [format_claim(c) for c in claims]


def _review_claim(
    db: Session,
    claim_id: str,
    seller_id: str,
    new_status: str,
    action: str,
    comments: str | None,
) -> Dict[str, Any]:
    """Apply a seller's decision to a claim inside one transaction.

    The claim row is locked (``FOR UPDATE`` on PostgreSQL) so concurrent
    decisions cannot interleave their status/reason updates. Only the seller
    who owns the claim may decide; the AI recommendation is never applied
    automatically. Order/Payment/Shipment state is intentionally untouched,
    matching the original workflow.
    """
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if not claim:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    if claim.seller_id != seller_id:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to {action} this claim",
        )

    claim.status = new_status
    claim.reviewed_at = datetime.now(timezone.utc)
    if comments:
        claim.reason = f"{claim.reason} | Seller Comments: {comments}"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(claim)
    return format_claim(claim)


@router.post("/claims/{id}/approve", response_model=ClaimResponse)
def approve_claim(
    id: str,
    payload: ClaimDecisionRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    return _review_claim(
        db, id, current_seller["id"], "APPROVED", "approve", payload.comments
    )


@router.post("/claims/{id}/reject", response_model=ClaimResponse)
def reject_claim(
    id: str,
    payload: ClaimDecisionRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    return _review_claim(
        db, id, current_seller["id"], "REJECTED", "reject", payload.comments
    )


@router.get("/crm-tags", response_model=List[CRMTagResponse])
def list_crm_tags(
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    tags = db.scalars(
        select(CRMTag)
        .where(CRMTag.seller_id == current_seller["id"])
        .order_by(CRMTag.created_at, CRMTag.id)
    ).all()
    return [_format_tag(t) for t in tags]


_DUPLICATE_TAG = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="CRM Tag with this name already exists",
)


@router.post("/crm-tags", response_model=CRMTagResponse)
def create_crm_tag(
    payload: CRMTagCreateRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    seller_id = current_seller["id"]

    # Serialize tag creation per seller: on PostgreSQL this row lock makes a
    # concurrent request wait, and its duplicate check (below) then sees the
    # committed tag. The DB unique constraint (seller_id, name) is
    # case-sensitive, so it alone cannot enforce the case-insensitive rule.
    db.scalar(select(User.id).where(User.id == seller_id).with_for_update())

    # Case-insensitive duplicate check, using Python str.lower() exactly as
    # the original in-memory implementation did (avoids DB collation
    # differences in SQL LOWER()).
    wanted = payload.name.lower()
    existing_names = db.scalars(
        select(CRMTag.name).where(CRMTag.seller_id == seller_id)
    ).all()
    if any(name.lower() == wanted for name in existing_names):
        db.rollback()
        raise _DUPLICATE_TAG

    tag = CRMTag(
        id=str(uuid.uuid4()),
        seller_id=seller_id,
        name=payload.name,
        created_at=datetime.now(timezone.utc),
    )
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        # Exact-name race caught by uq_crm_tags_seller_name; DB details hidden.
        db.rollback()
        raise _DUPLICATE_TAG
    except Exception:
        db.rollback()
        raise
    db.refresh(tag)
    return _format_tag(tag)


@router.post("/customers/{customer_id}/tags/{tag_id}")
def associate_crm_tag(
    customer_id: str,
    tag_id: str,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    tag = db.get(CRMTag, tag_id)
    if not tag or tag.seller_id != current_seller["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this CRM tag or it does not exist",
        )

    if not db.get(User, customer_id):
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    success = {"success": True, "message": "CRM tag associated successfully"}

    def _association_exists() -> bool:
        return (
            db.scalar(
                select(UserCRMTag.id).where(
                    UserCRMTag.user_id == customer_id, UserCRMTag.tag_id == tag_id
                )
            )
            is not None
        )

    # Idempotent: an existing association is a success, as before.
    if _association_exists():
        return success

    db.add(
        UserCRMTag(
            id=str(uuid.uuid4()),
            user_id=customer_id,
            tag_id=tag_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # A concurrent request may have created the same association
        # (uq_user_crm_tags_user_tag); that is still a success.
        if _association_exists():
            return success
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to associate CRM tag",
        )
    except Exception:
        db.rollback()
        raise
    return success


@router.get("/orders", response_model=List[SellerOrderResponse])
def list_seller_orders(
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """List orders containing products belonging to the authenticated seller.

    Applies data masking: returns ONLY order items belonging to this seller.
    """
    seller_id = current_seller["id"]
    stmt = (
        select(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Product.seller_id == seller_id,
            Order.status != "CANCELLED",
        )
        .distinct()
        .order_by(Order.created_at.desc())
    )
    orders = db.scalars(stmt).all()

    result = []
    for o in orders:
        seller_items = []
        for item in o.items:
            prod = item.product or db.get(Product, item.product_id)
            if prod and prod.seller_id == seller_id:
                seller_items.append(
                    SellerOrderItemResponse(
                        id=str(item.id),
                        product_id=str(item.product_id),
                        stock_id=str(item.stock_id),
                        variant_key=str(item.variant_key),
                        quantity=cast(int, item.quantity),
                        unit_price=float(cast(Decimal, item.unit_price)),
                        product_name=str(prod.name) if prod.name is not None else None,
                    )
                )

        shipment = db.scalar(
            select(Shipment).where(
                Shipment.order_id == o.id,
                Shipment.seller_id == seller_id,
            )
        )
        shipment_data = None
        if shipment:
            shipment_data = {
                "id": shipment.id,
                "order_id": shipment.order_id,
                "seller_id": shipment.seller_id,
                "carrier_name": shipment.carrier_name,
                "tracking_number": shipment.tracking_number,
                "status": shipment.status,
                "estimated_delivery": shipment.estimated_delivery,
            }

        result.append(
            SellerOrderResponse(
                id=str(o.id),
                user_id=str(o.user_id),
                status=str(o.status),
                created_at=cast(datetime, o.created_at),
                items=seller_items,
                shipment=shipment_data,
            )
        )
    return result


@router.patch("/orders/{order_id}/shipment")
def update_seller_shipment(
    order_id: str,
    payload: SellerShipmentUpdateRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """Update shipment for the seller's items in the given order.

    - Validates order existence (404).
    - Defends against IDOR: checks seller owns items in the order (403).
    - Checks Order State: order must be PAID (400).
    - Prevents mutation if shipment is already DELIVERED (400).
    - Validates carrier_name & tracking_number are non-empty after trim before DISPATCHED (400).
    - Uses JWT-authenticated seller identity only; does NOT accept seller_id in payload.
    """
    seller_id = current_seller["id"]

    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    has_items = db.scalar(
        select(OrderItem.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            OrderItem.order_id == order_id,
            Product.seller_id == seller_id,
        )
    )
    if not has_items:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have products in this order",
        )

    if order.status != "PAID":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update shipment for order in status '{order.status}'. Order must be PAID.",
        )

    shipment = db.scalar(
        select(Shipment)
        .where(Shipment.order_id == order_id, Shipment.seller_id == seller_id)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if not shipment:
        shipment = Shipment(
            id=str(uuid.uuid4()),
            order_id=order_id,
            seller_id=seller_id,
            carrier_name="Standard Delivery",
            tracking_number=None,
            status="PREPARING",
            estimated_delivery=now + timedelta(days=3),
            created_at=now,
        )
        db.add(shipment)
        db.flush()

    if shipment.status == "DELIVERED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment has already been DELIVERED and cannot be modified.",
        )

    target_status = payload.status.strip().upper() if payload.status else shipment.status
    target_carrier = payload.carrier_name.strip() if payload.carrier_name is not None else shipment.carrier_name
    target_tracking = payload.tracking_number.strip() if payload.tracking_number is not None else shipment.tracking_number

    if target_status == "DISPATCHED":
        if not target_carrier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="carrier_name cannot be empty when dispatching shipment",
            )
        if not target_tracking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tracking_number cannot be empty when dispatching shipment",
            )

    shipment.status = target_status
    if payload.carrier_name is not None:
        shipment.carrier_name = target_carrier
    if payload.tracking_number is not None:
        shipment.tracking_number = target_tracking
    if payload.estimated_delivery is not None:
        shipment.estimated_delivery = payload.estimated_delivery

    try:
        db.commit()
        db.refresh(shipment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tracking number already exists or shipment conflict: {exc}",
        )
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "message": "Shipment updated successfully",
        "shipment": {
            "id": shipment.id,
            "order_id": shipment.order_id,
            "seller_id": shipment.seller_id,
            "carrier_name": shipment.carrier_name,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "estimated_delivery": shipment.estimated_delivery,
        },
    }