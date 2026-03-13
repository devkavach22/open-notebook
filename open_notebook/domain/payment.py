"""Payment domain models for Razorpay integration"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class PaymentMethod(BaseModel):
    """Payment method model"""
    id: Optional[str] = None
    user_id: str
    razorpay_customer_id: Optional[str] = None
    type: str  # 'card', 'upi', 'netbanking', 'wallet'
    card_brand: Optional[str] = None  # 'visa', 'mastercard', 'rupay'
    card_last4: Optional[str] = None
    upi_id: Optional[str] = None
    wallet_name: Optional[str] = None  # 'paytm', 'phonepe', 'googlepay'
    is_default: bool = False
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class Transaction(BaseModel):
    """Transaction model"""
    id: Optional[str] = None
    user_id: str
    subscription_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str  # 'created', 'authorized', 'captured', 'failed', 'refunded'
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    payment_method: Optional[str] = None  # 'card', 'upi', 'netbanking', 'wallet'
    description: str
    metadata: Optional[Dict[str, Any]] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class Invoice(BaseModel):
    """Invoice model"""
    id: Optional[str] = None
    user_id: str
    subscription_id: Optional[str] = None
    transaction_id: Optional[str] = None
    invoice_number: str
    amount: float
    currency: str = "INR"
    tax_amount: float = 0.0  # GST amount (18% in India)
    status: str  # 'draft', 'issued', 'paid', 'cancelled'
    due_date: datetime
    paid_date: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = []
    pdf_url: Optional[str] = None
    razorpay_invoice_id: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class Refund(BaseModel):
    """Refund model"""
    id: Optional[str] = None
    transaction_id: str
    user_id: str
    amount: float
    currency: str = "INR"
    reason: str
    status: str  # 'pending', 'processed', 'failed'
    razorpay_refund_id: Optional[str] = None
    speed: str = "normal"  # 'normal' or 'optimum' (instant refund)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


# Request/Response Models
class CreatePaymentMethodRequest(BaseModel):
    user_id: str
    razorpay_customer_id: Optional[str] = None
    type: str
    is_default: bool = False


class CreateOrderRequest(BaseModel):
    user_id: str
    plan_id: str
    email: str
    phone: str
    name: str
    coupon_code: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str
    plan_id: str


class CreateRefundRequest(BaseModel):
    transaction_id: str
    amount: Optional[float] = None  # None = full refund
    reason: str
    speed: str = "normal"  # 'normal' or 'optimum'
