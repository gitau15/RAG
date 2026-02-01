from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PaymentInitiationRequest(BaseModel):
    """Schema for payment initiation requests"""
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., gt=0, description="Payment amount in KES")
    phone_number: str = Field(..., description="Customer phone number")
    product_info: Dict[str, Any] = Field(..., description="Product/service information")
    collection_name: Optional[str] = Field(None, description="Associated collection name")
    currency: str = Field(default="KES", description="Currency code")

class PaymentInitiationResponse(BaseModel):
    """Schema for payment initiation responses"""
    success: bool
    payment_id: Optional[str] = None
    merchant_request_id: Optional[str] = None
    customer_message: Optional[str] = None
    amount: Optional[float] = None
    error: Optional[str] = None

class PaymentStatusRequest(BaseModel):
    """Schema for payment status requests"""
    payment_id: str = Field(..., description="Payment identifier")

class PaymentStatusResponse(BaseModel):
    """Schema for payment status responses"""
    success: bool
    payment_id: str
    status: str
    result_code: Optional[str] = None
    result_desc: Optional[str] = None
    error: Optional[str] = None

class PaymentCallbackRequest(BaseModel):
    """Schema for payment callback requests from Daraja"""
    Body: Dict[str, Any]

class PaymentCallbackResponse(BaseModel):
    """Schema for payment callback responses to Daraja"""
    ResultCode: int
    ResultDesc: str

class PaymentHistoryItem(BaseModel):
    """Schema for individual payment history items"""
    payment_id: str
    amount: float
    status: str
    product: Dict[str, Any]
    created_at: datetime

class PaymentHistoryResponse(BaseModel):
    """Schema for payment history responses"""
    user_id: str
    payments: list[PaymentHistoryItem]
    total_amount: float

class ProductInfo(BaseModel):
    """Schema for product information"""
    name: str
    description: Optional[str] = None
    category: str
    price: float
    duration: Optional[int] = None  # Duration in days for subscriptions
    features: list[str] = []

# Sample product definitions
PREMIUM_SUBSCRIPTION = ProductInfo(
    name="Premium Subscription",
    description="Access to advanced RAG features and priority support",
    category="subscription",
    price=499.0,
    duration=30,
    features=["Advanced analytics", "Priority processing", "Custom integrations", "24/7 support"]
)

DOCUMENT_ACCESS = ProductInfo(
    name="Document Collection Access",
    description="Access to premium document collections",
    category="document_access",
    price=199.0,
    features=["Full document access", "Advanced search", "Export capabilities"]
)

PAY_PER_USE = ProductInfo(
    name="Pay-Per-Use Credits",
    description="Credits for individual document processing",
    category="credits",
    price=49.0,
    features=["100 processing credits", "Valid for 30 days", "Flexible usage"]
)