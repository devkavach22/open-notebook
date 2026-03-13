"""Payment API Routes for Razorpay Integration"""

from fastapi import APIRouter, HTTPException, Header, Request
from typing import List
from loguru import logger

from api.payment_service import PaymentService
from api.pricing_service import PricingService
from open_notebook.domain.payment import (
    Transaction,
    Invoice,
    Refund,
    CreateOrderRequest,
    VerifyPaymentRequest,
    CreateRefundRequest,
)

router = APIRouter(prefix="/payment", tags=["payment"])


# ==================== ORDER CREATION ====================

@router.post("/create-order")
async def create_order(request: CreateOrderRequest):
    """Create Razorpay order for payment"""
    try:
        # Get plan details
        plan = await PricingService.get_plan_by_id(request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Apply coupon if provided
        amount = plan.price
        if request.coupon_code:
            # TODO: Apply coupon discount from discount_service
            pass
        
        # Create order
        order = await PaymentService.create_subscription_payment(
            user_id=request.user_id,
            plan_id=request.plan_id,
            email=request.email,
            phone=request.phone,
            name=request.name
        )
        
        return order
        
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PAYMENT VERIFICATION ====================

@router.post("/verify")
async def verify_payment(request: VerifyPaymentRequest):
    """Verify payment after Razorpay checkout"""
    try:
        # Capture and verify payment
        transaction = await PaymentService.capture_payment(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature,
            user_id=request.user_id
        )
        
        # If payment successful, create subscription
        if transaction.status == "captured":
            subscription = await PricingService.subscribe_user(
                request.user_id, 
                request.plan_id
            )
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "subscription_id": subscription.id,
                "message": "Payment successful and subscription activated"
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail="Payment not captured"
            )
        
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== TRANSACTIONS ====================

@router.get("/transactions/{user_id}", response_model=List[Transaction])
async def get_transactions(user_id: str, limit: int = 50):
    """Get transaction history for a user"""
    try:
        return await PaymentService.get_user_transactions(user_id, limit)
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/order/{order_id}", response_model=Transaction)
async def get_transaction_by_order(order_id: str):
    """Get transaction by Razorpay order ID"""
    try:
        transaction = await PaymentService.get_transaction_by_order_id(order_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction
    except Exception as e:
        logger.error(f"Get transaction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== INVOICES ====================

@router.get("/invoices/{user_id}", response_model=List[Invoice])
async def get_invoices(user_id: str):
    """Get all invoices for a user"""
    try:
        return await PaymentService.get_user_invoices(user_id)
    except Exception as e:
        logger.error(f"Get invoices error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices/detail/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    """Get a specific invoice"""
    try:
        invoice = await PaymentService.get_invoice_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except Exception as e:
        logger.error(f"Get invoice error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== REFUNDS ====================

@router.post("/refunds", response_model=Refund)
async def create_refund(request: CreateRefundRequest):
    """Create a refund for a transaction"""
    try:
        # Get transaction to extract user_id
        from open_notebook.database.repository import repo_query
        trans_query = f"SELECT * FROM {request.transaction_id}"
        trans_result = await repo_query(trans_query)
        
        if not trans_result:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        user_id = trans_result[0]["user_id"]
        
        # Create refund
        refund = await PaymentService.create_refund(
            transaction_id=request.transaction_id,
            user_id=user_id,
            amount=request.amount,
            reason=request.reason,
            speed=request.speed
        )
        
        return refund
        
    except Exception as e:
        logger.error(f"Refund creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/refunds/{transaction_id}", response_model=List[Refund])
async def get_refunds(transaction_id: str):
    """Get all refunds for a transaction"""
    try:
        return await PaymentService.get_transaction_refunds(transaction_id)
    except Exception as e:
        logger.error(f"Get refunds error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== WEBHOOKS ====================

@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None)
):
    """Handle Razorpay webhooks"""
    try:
        # Get raw body
        body = await request.body()
        payload = body.decode('utf-8')
        
        # Verify webhook signature
        is_valid = PaymentService.verify_webhook_signature(
            payload=payload,
            signature=x_razorpay_signature
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse event data
        import json
        event_data = json.loads(payload)
        event_type = event_data.get("event")
        
        # Handle webhook
        await PaymentService.handle_webhook(
            event_type=event_type,
            event_data=event_data
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
