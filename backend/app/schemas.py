from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = Field("buyer", description="Must be 'buyer' or 'seller'")
    name: Optional[str] = Field(None, max_length=255)
    store_name: Optional[str] = Field(None, max_length=255)

class BecomeSellerRequest(BaseModel):
    store_name: str = Field(..., min_length=2, max_length=255, description="Name of the boutique or atelier")

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    store_name: Optional[str] = Field(None, max_length=255)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    created_at: datetime
    name: Optional[str] = None
    store_name: Optional[str] = None

    class Config:
        orm_mode = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class StockResponse(BaseModel):
    id: str
    product_id: str
    variant_key: str
    available_quantity: int
    updated_at: datetime

class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    stock_quantity: int
    category: str
    seller_id: str
    is_active: bool
    image_url: Optional[str] = None
    color: Optional[str] = None
    variants: Optional[List[StockResponse]] = []

CATEGORIES: List[str] = [
    "T-Shirts",
    "Shirts",
    "Hoodies & Sweatshirts",
    "Jackets",
    "Shorts",
    "Long Pants",
    "Accessories",
]


class StockCreateItem(BaseModel):
    variant_key: str = Field(..., max_length=50)
    available_quantity: int = Field(..., ge=0)

class ProductCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: str
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(0, ge=0)
    category: str = Field(..., max_length=100)
    image_url: Optional[str] = Field(None, max_length=1024)
    color: Optional[str] = Field(None, max_length=50)
    variants: Optional[List[StockCreateItem]] = None

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1024)
    color: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    variants: Optional[List[StockCreateItem]] = None

class StockCheckRequest(BaseModel):
    product_id: str
    variant_key: str
    quantity: int

class StockCheckResponse(BaseModel):
    product_id: str
    variant_key: str
    requested_quantity: int
    available_quantity: int
    is_fulfillable: bool

class FastLinkRequest(BaseModel):
    product_id: str
    variant_key: str
    quantity: int

class FastLinkResponse(BaseModel):
    token: str
    expires_at: datetime
    checkout_url: str

class FastLinkSessionResponse(BaseModel):
    id: str
    user_id: str
    product_id: str
    stock_id: str
    variant_key: str
    quantity: int
    expires_at: datetime
    status: str
    is_fulfillable: bool
    available_quantity: int

class OrderItemRequest(BaseModel):
    product_id: str
    variant_key: str
    quantity: int

class OrderCreateRequest(BaseModel):
    items: List[OrderItemRequest]

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    stock_id: str
    variant_key: str
    quantity: int
    unit_price: float

class OrderResponse(BaseModel):
    id: str
    user_id: str
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]
    payment: Optional[Dict[str, Any]] = None
    shipment: Optional[Dict[str, Any]] = None
    shipments: Optional[List[Dict[str, Any]]] = None

class SellerShipmentUpdateRequest(BaseModel):
    carrier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = None
    estimated_delivery: Optional[datetime] = None

class SellerOrderItemResponse(BaseModel):
    id: str
    product_id: str
    stock_id: str
    variant_key: str
    quantity: int
    unit_price: float
    product_name: Optional[str] = None

class SellerOrderResponse(BaseModel):
    id: str
    user_id: str
    status: str
    created_at: datetime
    items: List[SellerOrderItemResponse]
    shipment: Optional[Dict[str, Any]] = None

class SlipUploadRequest(BaseModel):
    order_id: str
    slip_reference: str

class SlipUploadResponse(BaseModel):
    order_id: str
    payment_id: str
    slip_status: str
    verification_status: str
    message: str
    receipt: Optional[Dict[str, Any]] = None

class SimulatePaymentRequest(BaseModel):
    outcome: Optional[str] = "SUCCESS"
    payment_method: Optional[str] = "SIMULATED_CARD"
    failure_reason: Optional[str] = None

class SimulatePaymentResponse(BaseModel):
    success: bool
    message: str
    order: OrderResponse
    payment_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    order_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    escalation_required: bool
    suggested_action: Optional[str] = None

class LogisticsCheckRequest(BaseModel):
    tracking_number: str

class LogisticsCheckResponse(BaseModel):
    tracking_number: str
    status: str
    anomaly_detected: bool
    ticket_created: bool
    ticket_id: Optional[str] = None
    message: str

class ClaimSubmitRequest(BaseModel):
    order_id: str
    reason: str

class ClaimResponse(BaseModel):
    id: str
    order_id: str
    buyer_id: str
    seller_id: str
    reason: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    ai_recommendation: Optional[str] = None

class ClaimDecisionRequest(BaseModel):
    comments: Optional[str] = None

class CRMTagCreateRequest(BaseModel):
    name: str

class CRMTagResponse(BaseModel):
    id: str
    seller_id: str
    name: str
    created_at: datetime