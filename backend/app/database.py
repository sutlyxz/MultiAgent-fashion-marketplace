import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Mapping, Optional
import threading

from app.config import settings

db_lock = threading.Lock()

class Database:
    def __init__(self):
        self.users = []
        self.products = []
        self.stocks = []
        self.carts = []
        self.cart_items = []
        self.checkout_sessions = []
        self.orders = []
        self.order_items = []
        self.payments = []
        self.shipments = []
        self.support_tickets = []
        self.claims = []
        self.crm_tags = []
        self.user_crm_tags = []
        self._seed()

    def _seed(self):
        seller_id = "11111111-1111-1111-1111-111111111111"
        buyer_id = "22222222-2222-2222-2222-222222222222"

        self.users.append({
            "id": seller_id,
            "email": "seller@fashion.com",
            "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.oMqp7OUMyY1Zp980SBv3Wp63ZpP6q",
            "role": "seller",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        self.users.append({
            "id": buyer_id,
            "email": "buyer@fashion.com",
            "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.oMqp7OUMyY1Zp980SBv3Wp63ZpP6q",
            "role": "buyer",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        tag1_id = "88888888-8888-8888-8888-888888888888"
        self.crm_tags.append({
            "id": tag1_id,
            "seller_id": seller_id,
            "name": "VIP Buyer",
            "created_at": datetime.utcnow()
        })

db = Database()

def verify_payment_and_decrement_stock(
    order_id: str,
    payment_id: str,
    slip_reference: str,
    verification_result: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply a verifier result only when amount and configured recipient match."""
    with db_lock:
        payment = next((p for p in db.payments if p["id"] == payment_id), None)
        if not payment:
            return {"success": False, "message": "Payment record not found"}

        order = next((o for o in db.orders if o["id"] == order_id), None)
        if not order:
            return {"success": False, "message": "Order not found"}

        if payment["slip_status"] == "VERIFIED":
            return {"success": True, "message": "Payment already verified", "order": order}

        if payment.get("slip_reference") != slip_reference:
            return {
                "success": False,
                "message": "Slip evidence changed; payment verification is unavailable. Stock was not deducted.",
                "order": order,
            }

        if not isinstance(verification_result, Mapping):
            payment["slip_status"] = "UPLOADED"
            payment["verification_status"] = "UNAVAILABLE"
            return {
                "success": False,
                "message": "Payment verification unavailable. Slip evidence was stored; stock was not deducted.",
                "order": order,
            }

        recipient_account = settings.PAYMENT_RECIPIENT_ACCOUNT.strip()
        if not recipient_account:
            payment["slip_status"] = "UPLOADED"
            payment["verification_status"] = "UNAVAILABLE"
            return {
                "success": False,
                "message": "Payment verification unavailable because the recipient account is not configured. Stock was not deducted.",
                "order": order,
            }

        try:
            verified_amount = Decimal(str(verification_result.get("amount")))
            order_amount = Decimal(str(order["total_amount"]))
        except (InvalidOperation, TypeError, ValueError):
            verified_amount = Decimal("NaN")
            order_amount = Decimal(str(order["total_amount"]))

        verification_succeeded = (
            verification_result.get("verified") is True
            and verified_amount.is_finite()
            and order_amount.is_finite()
            and verified_amount == order_amount
            and verification_result.get("destination_account") == recipient_account
        )
        if not verification_succeeded:
            payment["slip_status"] = "REJECTED"
            payment["verification_status"] = "REJECTED"
            return {
                "success": False,
                "message": "Payment verification failed. Stock was not deducted.",
                "order": order,
            }

        items = [item for item in db.order_items if item["order_id"] == order_id]
        if not items:
            return {
                "success": False,
                "message": "Order has no items; payment cannot be fulfilled.",
                "order": order,
            }

        required_quantities: Dict[str, int] = {}
        for item in items:
            stock_id = item["stock_id"]
            required_quantities[stock_id] = (
                required_quantities.get(stock_id, 0) + item["quantity"]
            )

        insufficient_stock_ids = []
        for stock_id, required_quantity in required_quantities.items():
            stock = next((s for s in db.stocks if s["id"] == stock_id), None)
            if not stock or stock["available_quantity"] < required_quantity:
                insufficient_stock_ids.append(stock_id)

        if insufficient_stock_ids:
            order["status"] = "MANUAL_RESOLUTION_REQUIRED"
            order["updated_at"] = datetime.utcnow()
            payment["slip_status"] = "VERIFIED"
            payment["verification_status"] = "VERIFIED"
            payment["verified_at"] = datetime.utcnow()
            payment["verification_reference"] = verification_result.get("reference")
            return {
                "success": False,
                "message": "Insufficient stock for one or more items. Order flagged for manual resolution.",
                "order": order
            }

        for item in items:
            stock = next((s for s in db.stocks if s["id"] == item["stock_id"]), None)
            if stock:
                stock["available_quantity"] -= item["quantity"]
                stock["updated_at"] = datetime.utcnow()

            product = next((p for p in db.products if p["id"] == item["product_id"]), None)
            if product:
                product["stock_quantity"] = sum(s["available_quantity"] for s in db.stocks if s["product_id"] == product["id"])

        payment["slip_status"] = "VERIFIED"
        payment["verification_status"] = "VERIFIED"
        payment["verified_at"] = datetime.utcnow()
        payment["verification_reference"] = verification_result.get("reference")

        order["status"] = "PAID"
        order["updated_at"] = datetime.utcnow()

        shipment_id = str(uuid.uuid4())
        db.shipments.append({
            "id": shipment_id,
            "order_id": order_id,
            "carrier_name": "FashionExpress",
            "tracking_number": f"FE-{uuid.uuid4().hex[:10].upper()}",
            "status": "PREPARING",
            "estimated_delivery": datetime.utcnow() + timedelta(days=3)
        })

        return {
            "success": True,
            "message": "Payment verified and stock decremented successfully.",
            "order": order,
            "receipt": {
                "receipt_id": f"REC-{uuid.uuid4().hex[:8].upper()}",
                "order_id": order_id,
                "amount": float(order["total_amount"]),
                "issued_at": datetime.utcnow().isoformat()
            }
        }