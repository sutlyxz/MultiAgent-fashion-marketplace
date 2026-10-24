from datetime import datetime, timedelta, timezone
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db_connection import get_db
from app.models import CheckoutSession, Product, Stock
from app.schemas import FastLinkRequest, FastLinkResponse, FastLinkSessionResponse

router = APIRouter(prefix="/checkout", tags=["Checkout"])


def _hash_token(token: str) -> str:
    """Compute SHA-256 hash of plaintext token string for secure storage/lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/fast-link", response_model=FastLinkResponse)
def create_fast_link(
    payload: FastLinkRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero",
        )

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # FR-02: Sellers cannot purchase their own products via fast-link checkout
    if product.seller_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sellers cannot purchase their own products",
        )

    stmt = select(Stock).where(
        Stock.product_id == payload.product_id,
        Stock.variant_key == payload.variant_key,
    )
    stock = db.scalar(stmt)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    token = f"FL-{uuid.uuid4().hex}"
    token_hash_val = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    checkout_session = CheckoutSession(
        id=str(uuid.uuid4()),
        token_hash=token_hash_val,
        user_id=current_user["id"],
        product_id=payload.product_id,
        stock_id=stock.id,
        variant_key=payload.variant_key,
        quantity=payload.quantity,
        expires_at=expires_at,
        status="OPEN",
    )

    try:
        db.add(checkout_session)
        db.commit()
        db.refresh(checkout_session)
    except Exception:
        db.rollback()
        raise

    return {
        "token": token,
        "expires_at": expires_at,
        "checkout_url": f"/checkout/fast-link/{token}",
    }


@router.get("/fast-link/{token}", response_model=FastLinkSessionResponse)
def get_fast_link_session(
    token: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_hash_val = _hash_token(token)
    stmt = select(CheckoutSession).where(CheckoutSession.token_hash == token_hash_val)
    session = db.scalar(stmt)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found",
        )

    if session.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this checkout session",
        )

    now = datetime.now(timezone.utc)
    expires_at_utc = session.expires_at
    if expires_at_utc.tzinfo is None:
        expires_at_utc = expires_at_utc.replace(tzinfo=timezone.utc)

    if now > expires_at_utc or session.status == "EXPIRED":
        if session.status != "EXPIRED":
            session.status = "EXPIRED"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout session has expired",
        )

    stock = db.get(Stock, session.stock_id)
    available_qty = stock.available_quantity if stock else 0
    is_fulfillable = available_qty >= session.quantity

    return {
        "id": session.id,
        "user_id": session.user_id,
        "product_id": session.product_id,
        "stock_id": session.stock_id,
        "variant_key": session.variant_key,
        "quantity": session.quantity,
        "expires_at": session.expires_at,
        "status": session.status,
        "is_fulfillable": is_fulfillable,
        "available_quantity": available_qty,
    }