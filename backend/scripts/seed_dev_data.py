"""Development seed script for PostgreSQL.

Seeds initial data from app.database into PostgreSQL (User -> Product -> Stock -> CRMTag).
Uses existing SQLAlchemy ORM models and session management.
Ensures idempotency, transactional integrity, and safe conflict handling.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys
from typing import Dict, Optional

from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path so app.* imports resolve
BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import db
from app.db_connection import _configured_session_factory
from app.models import CRMTag, Product, Stock, User


class SeedConflictError(RuntimeError):
    """Raised when an existing record with the same ID has conflicting field values."""
    pass


def make_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime object is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def seed_database(session: Session) -> Dict[str, int]:
    """Seed sample data from app.database into the database session.

    Returns summary dictionary with counts of inserted and skipped records.
    Raises SeedConflictError on data mismatches and rolls back the transaction.
    """
    summary = {
        "users_inserted": 0,
        "users_skipped": 0,
        "products_inserted": 0,
        "products_skipped": 0,
        "stocks_inserted": 0,
        "stocks_skipped": 0,
        "crm_tags_inserted": 0,
        "crm_tags_skipped": 0,
    }

    try:
        # 1. Seed Users (Seller and Buyer)
        for user_data in db.users:
            user_id = user_data["id"]
            existing = session.get(User, user_id)

            created_at = make_utc_aware(user_data["created_at"])
            updated_at = make_utc_aware(user_data["updated_at"])

            if existing:
                if (
                    existing.email != user_data["email"]
                    or existing.password_hash != user_data["password_hash"]
                    or existing.role != user_data["role"]
                ):
                    raise SeedConflictError(
                        f"Conflict for User ID {user_id}: Existing data in database "
                        f"does not match seed data."
                    )
                summary["users_skipped"] += 1
            else:
                new_user = User(
                    id=user_id,
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    role=user_data["role"],
                    created_at=created_at,
                    updated_at=updated_at,
                )
                session.add(new_user)
                summary["users_inserted"] += 1

        session.flush()

        # 2. Seed Products
        for product_data in db.products:
            p_id = product_data["id"]

            # Calculate and verify aggregate stock quantity against variant stocks
            matching_stocks = [s for s in db.stocks if s["product_id"] == p_id]
            calculated_stock = sum(s["available_quantity"] for s in matching_stocks)
            if product_data["stock_quantity"] != calculated_stock:
                raise ValueError(
                    f"Product {p_id} stock_quantity ({product_data['stock_quantity']}) "
                    f"does not match sum of variant stocks ({calculated_stock})"
                )

            existing = session.get(Product, p_id)
            price_decimal = Decimal(str(product_data["price"]))

            if existing:
                if (
                    existing.name != product_data["name"]
                    or existing.description != product_data["description"]
                    or Decimal(str(existing.price)) != price_decimal
                    or existing.stock_quantity != product_data["stock_quantity"]
                    or existing.category != product_data["category"]
                    or existing.seller_id != product_data["seller_id"]
                    or existing.is_active != product_data["is_active"]
                ):
                    raise SeedConflictError(
                        f"Conflict for Product ID {p_id}: Existing data in database "
                        f"does not match seed data."
                    )
                summary["products_skipped"] += 1
            else:
                new_product = Product(
                    id=p_id,
                    name=product_data["name"],
                    description=product_data["description"],
                    price=price_decimal,
                    stock_quantity=product_data["stock_quantity"],
                    category=product_data["category"],
                    seller_id=product_data["seller_id"],
                    is_active=product_data["is_active"],
                )
                session.add(new_product)
                summary["products_inserted"] += 1

        session.flush()

        # 3. Seed Stocks
        for stock_data in db.stocks:
            s_id = stock_data["id"]
            existing = session.get(Stock, s_id)
            updated_at = make_utc_aware(stock_data["updated_at"])

            if existing:
                if (
                    existing.product_id != stock_data["product_id"]
                    or existing.variant_key != stock_data["variant_key"]
                    or existing.available_quantity != stock_data["available_quantity"]
                ):
                    raise SeedConflictError(
                        f"Conflict for Stock ID {s_id}: Existing data in database "
                        f"does not match seed data."
                    )
                summary["stocks_skipped"] += 1
            else:
                new_stock = Stock(
                    id=s_id,
                    product_id=stock_data["product_id"],
                    variant_key=stock_data["variant_key"],
                    available_quantity=stock_data["available_quantity"],
                    updated_at=updated_at,
                )
                session.add(new_stock)
                summary["stocks_inserted"] += 1

        # 4. Seed CRM Tags
        for tag_data in db.crm_tags:
            tag_id = tag_data["id"]
            existing = session.get(CRMTag, tag_id)
            created_at = make_utc_aware(tag_data["created_at"])

            if existing:
                if (
                    existing.seller_id != tag_data["seller_id"]
                    or existing.name != tag_data["name"]
                ):
                    raise SeedConflictError(
                        f"Conflict for CRMTag ID {tag_id}: Existing data in database "
                        f"does not match seed data."
                    )
                summary["crm_tags_skipped"] += 1
            else:
                new_tag = CRMTag(
                    id=tag_id,
                    seller_id=tag_data["seller_id"],
                    name=tag_data["name"],
                    created_at=created_at,
                )
                session.add(new_tag)
                summary["crm_tags_inserted"] += 1

        session.commit()
        return summary

    except Exception:
        session.rollback()
        raise


def main():
    print("Starting development data seeding...")
    try:
        session_factory = _configured_session_factory()
        with session_factory() as session:
            result = seed_database(session)
            print("Seeding completed successfully!")
            print(f"Summary: {result}")
    except Exception as e:
        print(f"Error during seeding: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
