"""AI agent workflows.

Phase E: logistics ticketing and claim submission use PostgreSQL via
SQLAlchemy (``Shipment``, ``SupportTicket``, ``Order``, ``OrderItem``,
``Product``, ``Claim``). The chat endpoint is stateless and unchanged.
"""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db_connection import get_db
from app.models import Claim, Order, OrderItem, Product, Shipment, SupportTicket
from app.routers.seller import format_claim
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ClaimResponse,
    ClaimSubmitRequest,
    LogisticsCheckRequest,
    LogisticsCheckResponse,
)
from app.services.ai_service import ai_service

router = APIRouter(prefix="/agent", tags=["AI Agent Workflows"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    result = ai_service.generate_chat_response(payload.message, payload.order_id)
    return result


@router.post("/logistics/check-and-ticket", response_model=LogisticsCheckResponse)
def check_and_ticket(
    payload: LogisticsCheckRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shipment = db.scalar(
        select(Shipment).where(Shipment.tracking_number == payload.tracking_number)
    )
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found with the provided tracking number",
        )
    shipment_status = shipment.status
    shipment_order_id = shipment.order_id
    # Lock the order row so concurrent retries for the same order serialize
    # on PostgreSQL; the "existing ticket" check below then sees any ticket a
    # previous request committed, preventing duplicates.
    order = db.scalar(
        select(Order).where(Order.id == shipment_order_id).with_for_update()
    )
    if not order:  # Unreachable while the shipments.order_id FK holds.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found with the provided tracking number",
        )

    # Ownership rule mirrors GET /api/orders/{id}: the buyer who owns the
    # order, or a seller account.
    if order.user_id != current_user["id"] and current_user.get("role") != "seller":
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to check this shipment",
        )

    existing_ticket = db.scalar(
        select(SupportTicket)
        .where(SupportTicket.order_id == order.id)
        .order_by(SupportTicket.created_at, SupportTicket.id)
        .limit(1)
    )
    if existing_ticket:
        existing_ticket_id = existing_ticket.id
        db.rollback()  # release the lock; nothing to write
        return {
            "tracking_number": payload.tracking_number,
            "status": shipment_status,
            "anomaly_detected": True,
            "ticket_created": False,
            "ticket_id": existing_ticket_id,
            "message": "A support ticket has already been created for this shipment.",
        }

    # Detection rule unchanged. Shipment data is the simulated record stored
    # in the database; no carrier integration exists.
    anomaly_detected = (
        shipment_status == "PREPARING" or "delay" in shipment_status.lower()
    )
    ticket_id = None
    message = "Shipment is on track. No anomaly detected."

    if anomaly_detected:
        ticket_id = str(uuid.uuid4())
        db.add(
            SupportTicket(
                id=ticket_id,
                order_id=shipment_order_id,
                user_id=current_user["id"],
                type="LOGISTICS_ANOMALY",
                status="OPEN",
                created_at=datetime.now(timezone.utc),
                assigned_to="Logistics Support Team",
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to create support ticket",
            )
        except Exception:
            db.rollback()
            raise
        message = "Logistics anomaly detected. A support ticket has been created automatically."
    else:
        db.rollback()  # release the lock; nothing to write

    return {
        "tracking_number": payload.tracking_number,
        "status": shipment_status,
        "anomaly_detected": anomaly_detected,
        "ticket_created": anomaly_detected,
        "ticket_id": ticket_id,
        "message": message,
    }


@router.post("/claim/submit", response_model=ClaimResponse)
def submit_claim(
    payload: ClaimSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to submit a claim for this order",
        )

    # The responsible seller is derived server-side from the order's products
    # (never from the client). Original behaviour used the first item; rows
    # have no insertion timestamp, so OrderItem.id gives a deterministic pick.
    seller_id = db.scalar(
        select(Product.seller_id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .where(OrderItem.order_id == order.id)
        .order_by(OrderItem.id)
        .limit(1)
    )
    if seller_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no items",
        )

    # Advisory only: stored for the seller to read, never applied automatically.
    ai_rec = ai_service.get_warranty_recommendation(payload.reason)

    claim = Claim(
        id=str(uuid.uuid4()),
        order_id=order.id,
        buyer_id=current_user["id"],
        seller_id=seller_id,
        reason=payload.reason,
        status="PENDING",
        submitted_at=datetime.now(timezone.utc),
        reviewed_at=None,
        ai_recommendation=ai_rec,
    )
    db.add(claim)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to submit claim",
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(claim)
    return format_claim(claim)