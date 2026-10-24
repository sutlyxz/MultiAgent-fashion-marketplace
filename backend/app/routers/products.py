from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, cast
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_seller, get_optional_current_user
from app.db_connection import get_db
from app.models import CheckoutSession, OrderItem, Product, Stock
from app.schemas import (
    CATEGORIES,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    StockCheckResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])


def _format_product(p: Product) -> dict:
    """Format a SQLAlchemy Product model instance to match ProductResponse schema."""
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "price": float(cast(Decimal, p.price)),
        "stock_quantity": p.stock_quantity,
        "category": p.category,
        "seller_id": p.seller_id,
        "is_active": p.is_active,
        "image_url": getattr(p, "image_url", None),
        "color": getattr(p, "color", None),
        "variants": [
            {
                "id": s.id,
                "product_id": s.product_id,
                "variant_key": s.variant_key,
                "available_quantity": s.available_quantity,
                "updated_at": s.updated_at,
            }
            for s in (p.stocks or [])
        ],
    }


@router.get("", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = Query(None, description="Search by product name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    color: Optional[str] = Query(None, description="Filter by color"),
    min_price: Optional[float] = Query(None, description="Filter by minimum price"),
    max_price: Optional[float] = Query(None, description="Filter by maximum price"),
    sort_by: Optional[str] = Query(None, description="Sort field, e.g. 'price'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .options(selectinload(Product.stocks))
        .where(Product.is_active == True)
    )

    # FR-01: When an authenticated seller accesses the shop, hide their own products
    if current_user and current_user.get("role") == "seller":
        seller_id = current_user.get("id")
        if seller_id:
            stmt = stmt.where(Product.seller_id != seller_id)

    if search:
        search_pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.name).like(search_pattern),
                func.lower(Product.description).like(search_pattern),
            )
        )

    if category:
        stmt = stmt.where(func.lower(Product.category) == category.lower())

    if color:
        stmt = stmt.where(func.lower(Product.color) == color.lower())

    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)

    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    if sort_by and sort_by.lower() == "price":
        if sort_order and sort_order.lower() == "desc":
            stmt = stmt.order_by(Product.price.desc(), Product.id.asc())
        else:
            stmt = stmt.order_by(Product.price.asc(), Product.id.asc())

    products = db.scalars(stmt).all()
    return [_format_product(p) for p in products]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    # Validate unique variant keys if variants provided
    if payload.variants:
        keys = [v.variant_key.strip().upper() for v in payload.variants]
        if len(keys) != len(set(keys)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variant keys must be unique",
            )
        computed_stock = sum(v.available_quantity for v in payload.variants)
    else:
        computed_stock = payload.stock_quantity

    # seller_id is ALWAYS taken from the authenticated seller, never trusted from client
    new_product = Product(
        id=str(uuid.uuid4()),
        name=payload.name.strip(),
        description=payload.description.strip(),
        price=Decimal(str(payload.price)),
        stock_quantity=computed_stock,
        category=payload.category.strip(),
        seller_id=current_seller["id"],
        image_url=payload.image_url.strip() if payload.image_url and payload.image_url.strip() else None,
        color=payload.color.strip() if payload.color and payload.color.strip() else None,
        is_active=True,
    )
    db.add(new_product)

    if payload.variants:
        now = datetime.now(timezone.utc)
        for v in payload.variants:
            stk = Stock(
                id=str(uuid.uuid4()),
                product_id=new_product.id,
                variant_key=v.variant_key.strip().upper(),
                available_quantity=v.available_quantity,
                updated_at=now,
            )
            db.add(stk)

    db.commit()
    db.refresh(new_product)
    return _format_product(new_product)


@router.get("/seller/me", response_model=List[ProductResponse])
def list_seller_products(
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .options(selectinload(Product.stocks))
        .where(Product.seller_id == current_seller["id"])
        .order_by(Product.name.asc(), Product.id.asc())
    )
    products = db.scalars(stmt).all()
    return [_format_product(p) for p in products]


@router.get("/check-stock", response_model=StockCheckResponse)
def check_stock(
    product_id: str,
    variant_key: str,
    quantity: int,
    db: Session = Depends(get_db),
):
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be a positive integer",
        )

    stmt = select(Stock).where(
        Stock.product_id == product_id,
        Stock.variant_key == variant_key,
    )
    stock = db.scalar(stmt)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    is_fulfillable = stock.available_quantity >= quantity
    return {
        "product_id": product_id,
        "variant_key": variant_key,
        "requested_quantity": quantity,
        "available_quantity": stock.available_quantity,
        "is_fulfillable": is_fulfillable,
    }


@router.get("/categories", response_model=List[str])
def list_categories() -> List[str]:
    """Return the 7 primary marketplace categories."""
    return CATEGORIES


@router.get("/{id}", response_model=ProductResponse)
def get_product(
    id: str,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .options(selectinload(Product.stocks))
        .where(Product.id == id)
    )
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return _format_product(product)


@router.patch("/{id}", response_model=ProductResponse)
@router.put("/{id}", response_model=ProductResponse)
def update_product(
    id: str,
    payload: ProductUpdateRequest,
    current_seller: dict = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .options(selectinload(Product.stocks))
        .where(Product.id == id)
    )
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Authorization check: only the owning seller can update this product
    if product.seller_id != current_seller["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this product",
        )

    try:
        if payload.name is not None:
            product.name = payload.name.strip()
        if payload.description is not None:
            product.description = payload.description.strip()
        if payload.price is not None:
            product.price = Decimal(str(payload.price))
        if payload.category is not None:
            product.category = payload.category.strip()
        if payload.image_url is not None:
            product.image_url = payload.image_url.strip() if payload.image_url.strip() else None
        if payload.color is not None:
            product.color = payload.color.strip() if payload.color.strip() else None
        if payload.is_active is not None:
            product.is_active = payload.is_active

        if payload.variants is not None:
            keys: List[str] = []
            for v in payload.variants:
                norm_key = v.variant_key.strip().upper() if v.variant_key else ""
                if not norm_key:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Variant key cannot be empty",
                    )
                if v.available_quantity < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Variant quantity cannot be negative",
                    )
                keys.append(norm_key)

            if len(keys) != len(set(keys)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Variant keys must be unique",
                )

            existing_stocks_by_key = {
                s.variant_key.strip().upper(): s for s in (product.stocks or [])
            }
            incoming_keys_set = set(keys)

            removed_stocks = [
                s for key, s in existing_stocks_by_key.items()
                if key not in incoming_keys_set
            ]

            if removed_stocks:
                removed_stock_ids = [s.id for s in removed_stocks]
                referenced_stock_ids = set(
                    db.scalars(
                        select(OrderItem.stock_id).where(OrderItem.stock_id.in_(removed_stock_ids))
                    ).all()
                )
                if referenced_stock_ids:
                    blocked_variants = [
                        s.variant_key for s in removed_stocks if s.id in referenced_stock_ids
                    ]
                    variants_str = ", ".join(f"'{k}'" for k in blocked_variants)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot remove variant(s) {variants_str} because they are referenced by existing orders. Consider setting available quantity to 0 instead.",
                    )

                for s in removed_stocks:
                    db.execute(delete(CheckoutSession).where(CheckoutSession.stock_id == s.id))
                    if s in product.stocks:
                        product.stocks.remove(s)
                    db.delete(s)

            now = datetime.now(timezone.utc)
            for v in payload.variants:
                norm_key = v.variant_key.strip().upper()
                if norm_key in existing_stocks_by_key:
                    stk = existing_stocks_by_key[norm_key]
                    stk.variant_key = norm_key
                    stk.available_quantity = v.available_quantity
                    stk.updated_at = now
                else:
                    new_stk = Stock(
                        id=str(uuid.uuid4()),
                        product_id=product.id,
                        variant_key=norm_key,
                        available_quantity=v.available_quantity,
                        updated_at=now,
                    )
                    db.add(new_stk)

            product.stock_quantity = sum(v.available_quantity for v in payload.variants)
        elif payload.stock_quantity is not None:
            if payload.stock_quantity < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stock quantity cannot be negative",
                )
            product.stock_quantity = payload.stock_quantity

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    # Re-query with refreshed stocks
    stmt = (
        select(Product)
        .options(selectinload(Product.stocks))
        .where(Product.id == id)
    )
    product = db.scalar(stmt)
    return _format_product(product)
