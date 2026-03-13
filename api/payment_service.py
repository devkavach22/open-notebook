"""Razorpay Payment Service - Complete Implementation"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from loguru import logger
import razorpay
import hmac
import hashlib
import os

from open_notebook.database.repository import repo_query, repo_create
from open_notebook.domain.payment import (
    PaymentMethod, Transaction, Invoice, Refund
)

# Initialize Razorpay Client
razorpay_client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID", "rzp_test_"),
        os.getenv("RAZORPAY_KEY_SECRET", "")
    )
)


class PaymentService:
    """Service for handling Razorpay payments, invoices, and refunds"""

    # ==================== CUSTOMER MANAGEMENT ====================
    
    @staticmethod
    async def create_or_get_customer(
        user_id: str, 
        email: str, 
        phone: str, 
        name: str
    ) -> str:
        """Create or get Razorpay customer ID"""
        try:
            # Check if customer already exists in our DB
            query = """
                SELECT razorpay_customer_id FROM payment_method 
                WHERE user_id = $user_id AND razorpay_customer_id IS NOT NULL
                LIMIT 1
            """
            result = await repo_query(query, {"user_id": user_id})
            
            if result and result[0].get("razorpay_customer_id"):
                logger.info(f"Found existing customer: {result[0]['razorpay_customer_id']}")
                return result[0]["razorpay_customer_id"]
            
            # Try to create new customer in Razorpay
            try:
                customer = razorpay_client.customer.create({
                    "name": name,
                    "email": email,
                    "contact": phone,
                    "notes": {
                        "user_id": user_id
                    }
                })
                
                logger.info(f"Created Razorpay customer: {customer['id']}")
                return customer["id"]
                
            except razorpay.errors.BadRequestError as e:
                error_msg = str(e)
                
                # If customer already exists in Razorpay, fetch it
                if "already exists" in error_msg.lower():
                    logger.info(f"Customer already exists in Razorpay for email: {email}")
                    
                    # Fetch all customers and find by email
                    customers = razorpay_client.customer.all()
                    for cust in customers.get('items', []):
                        if cust.get('email') == email:
                            logger.info(f"Found existing Razorpay customer: {cust['id']}")
                            return cust['id']
                    
                    # If not found, create with a unique email
                    import time
                    unique_email = f"{user_id}_{int(time.time())}@{email.split('@')[1]}"
                    customer = razorpay_client.customer.create({
                        "name": name,
                        "email": unique_email,
                        "contact": phone,
                        "notes": {
                            "user_id": user_id,
                            "original_email": email
                        }
                    })
                    logger.info(f"Created customer with unique email: {customer['id']}")
                    return customer["id"]
                else:
                    raise Exception(f"Failed to create customer: {error_msg}")
            
        except Exception as e:
            logger.error(f"Customer creation/fetch error: {e}")
            raise Exception(f"Failed to create customer: {str(e)}")

    # ==================== ORDER CREATION ====================
    
    @staticmethod
    async def create_order(
        user_id: str,
        amount: float,
        currency: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a Razorpay order"""
        try:
            logger.info(f"=== CREATE_ORDER DEBUG v2 ===")
            logger.info(f"Creating order for user {user_id}, amount {amount} {currency}")
            
            # Convert amount to paise (smallest currency unit)
            amount_in_paise = int(amount * 100)
            
            # Create order in Razorpay
            order = razorpay_client.order.create({
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": f"rcpt_{user_id}_{int(datetime.now().timestamp())}",
                "notes": metadata or {}
            })
            
            # Create transaction record in DB
            transaction_data = {
                "user_id": user_id,
                "amount": amount,
                "currency": currency,
                "status": "created",
                "razorpay_order_id": order["id"],
                "description": description,
                "metadata": metadata,
            }
            
            db_result = await repo_create("transaction", transaction_data)
            
            # Handle if db_result is a list (SurrealDB sometimes returns [record] instead of record)
            if isinstance(db_result, list) and len(db_result) > 0:
                db_result = db_result[0]
            
            logger.info(f"Created Razorpay order: {order['id']}, transaction: {db_result.get('id')}")
            
            return {
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "transaction_id": db_result["id"],
                "key_id": os.getenv("RAZORPAY_KEY_ID")
            }
            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay order creation error: {e}")
            raise Exception(f"Failed to create order: {str(e)}")

    # ==================== PAYMENT VERIFICATION ====================
    
    @staticmethod
    def verify_payment_signature(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """Verify Razorpay payment signature for security"""
        try:
            # Create signature string
            message = f"{razorpay_order_id}|{razorpay_payment_id}"
            
            # Generate expected signature
            key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
            generated_signature = hmac.new(
                key_secret,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(generated_signature, razorpay_signature)
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    async def capture_payment(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        user_id: str
    ) -> Transaction:
        """Capture and verify payment after user completes checkout"""
        try:
            # Verify signature first (SECURITY)
            is_valid = PaymentService.verify_payment_signature(
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature
            )
            
            if not is_valid:
                logger.error("Invalid payment signature!")
                raise Exception("Payment verification failed - invalid signature")
            
            # Fetch payment details from Razorpay
            payment = razorpay_client.payment.fetch(razorpay_payment_id)
            
            # Update transaction in DB
            update_query = """
                UPDATE transaction 
                SET 
                    status = $status,
                    razorpay_payment_id = $payment_id,
                    razorpay_signature = $signature,
                    payment_method = $method,
                    updated = time::now()
                WHERE razorpay_order_id = $order_id
                RETURN AFTER
            """
            
            result = await repo_query(update_query, {
                "status": "captured" if payment["status"] == "captured" else "authorized",
                "payment_id": razorpay_payment_id,
                "signature": razorpay_signature,
                "method": payment.get("method", "unknown"),
                "order_id": razorpay_order_id
            })
            
            if not result:
                raise Exception("Transaction not found")
            
            transaction = result[0]
            
            # Generate invoice if payment captured
            if payment["status"] == "captured":
                await PaymentService.generate_invoice(
                    user_id=user_id,
                    transaction_id=transaction["id"],
                    amount=transaction["amount"],
                    currency=transaction["currency"],
                    description=transaction["description"]
                )
            
            logger.info(f"Payment captured: {razorpay_payment_id}")
            return Transaction(**transaction)
            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay payment capture error: {e}")
            raise Exception(f"Failed to capture payment: {str(e)}")

    # ==================== PAYMENT HISTORY ====================
    
    @staticmethod
    async def get_user_transactions(
        user_id: str,
        limit: int = 50
    ) -> List[Transaction]:
        """Get transaction history for a user"""
        query = """
            SELECT * FROM transaction 
            WHERE user_id = $user_id 
            ORDER BY created DESC 
            LIMIT $limit
        """
        result = await repo_query(query, {"user_id": user_id, "limit": limit})
        return [Transaction(**t) for t in result] if result else []
    
    @staticmethod
    async def get_transaction_by_order_id(order_id: str) -> Optional[Transaction]:
        """Get transaction by Razorpay order ID"""
        query = """
            SELECT * FROM transaction 
            WHERE razorpay_order_id = $order_id
            LIMIT 1
        """
        result = await repo_query(query, {"order_id": order_id})
        return Transaction(**result[0]) if result else None

    # ==================== INVOICES ====================
    
    @staticmethod
    async def generate_invoice(
        user_id: str,
        transaction_id: str,
        amount: float,
        currency: str,
        description: str,
        subscription_id: Optional[str] = None
    ) -> Invoice:
        """Generate an invoice for a transaction"""
        
        # Calculate GST (18% in India)
        base_amount = amount / 1.18  # Remove GST from total
        gst_amount = amount - base_amount
        
        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{transaction_id.split(':')[1][:8].upper()}"
        
        invoice_data = {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "transaction_id": transaction_id,
            "invoice_number": invoice_number,
            "amount": amount,
            "currency": currency,
            "tax_amount": gst_amount,
            "status": "paid",
            "due_date": datetime.now(timezone.utc),
            "paid_date": datetime.now(timezone.utc),
            "line_items": [
                {
                    "description": description,
                    "amount": base_amount,
                    "quantity": 1,
                    "tax_rate": 18.0,
                    "tax_amount": gst_amount,
                }
            ],
        }
        
        result = await repo_create("invoice", invoice_data)
        
        # Handle if result is a list
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        
        logger.info(f"Generated invoice: {invoice_number}")
        return Invoice(**result)
    
    @staticmethod
    async def get_user_invoices(user_id: str) -> List[Invoice]:
        """Get all invoices for a user"""
        query = """
            SELECT * FROM invoice 
            WHERE user_id = $user_id 
            ORDER BY created DESC
        """
        result = await repo_query(query, {"user_id": user_id})
        return [Invoice(**inv) for inv in result] if result else []
    
    @staticmethod
    async def get_invoice_by_id(invoice_id: str) -> Optional[Invoice]:
        """Get a specific invoice"""
        query = f"SELECT * FROM {invoice_id}"
        result = await repo_query(query)
        return Invoice(**result[0]) if result else None

    # ==================== REFUNDS ====================
    
    @staticmethod
    async def create_refund(
        transaction_id: str,
        user_id: str,
        amount: Optional[float],
        reason: str,
        speed: str = "normal"
    ) -> Refund:
        """Create a refund for a transaction"""
        try:
            # Get transaction
            trans_query = f"SELECT * FROM {transaction_id}"
            trans_result = await repo_query(trans_query)
            
            if not trans_result:
                raise Exception("Transaction not found")
            
            transaction = trans_result[0]
            
            if not transaction.get("razorpay_payment_id"):
                raise Exception("No payment ID found for this transaction")
            
            # Determine refund amount
            refund_amount = amount if amount else transaction["amount"]
            refund_amount_paise = int(refund_amount * 100)
            
            # Create Razorpay refund
            razorpay_refund = razorpay_client.payment.refund(
                transaction["razorpay_payment_id"],
                {
                    "amount": refund_amount_paise,
                    "speed": speed,
                    "notes": {
                        "reason": reason,
                        "user_id": user_id
                    }
                }
            )
            
            # Create refund record
            refund_data = {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "amount": refund_amount,
                "currency": transaction["currency"],
                "reason": reason,
                "status": "processed" if razorpay_refund["status"] == "processed" else "pending",
                "razorpay_refund_id": razorpay_refund["id"],
                "speed": speed,
            }
            
            result = await repo_create("refund", refund_data)
            
            # Handle if result is a list
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            # Update transaction status
            update_query = f"""
                UPDATE {transaction_id} 
                SET status = 'refunded', updated = time::now()
            """
            await repo_query(update_query)
            
            logger.info(f"Created refund: {razorpay_refund['id']}")
            return Refund(**result)
            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay refund error: {e}")
            raise Exception(f"Failed to process refund: {str(e)}")
    
    @staticmethod
    async def get_transaction_refunds(transaction_id: str) -> List[Refund]:
        """Get all refunds for a transaction"""
        query = """
            SELECT * FROM refund 
            WHERE transaction_id = $transaction_id 
            ORDER BY created DESC
        """
        result = await repo_query(query, {"transaction_id": transaction_id})
        return [Refund(**r) for r in result] if result else []

    # ==================== WEBHOOKS ====================
    
    @staticmethod
    def verify_webhook_signature(payload: str, signature: str) -> bool:
        """Verify Razorpay webhook signature"""
        try:
            key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
            expected_signature = hmac.new(
                key_secret,
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False
    
    @staticmethod
    async def handle_webhook(event_type: str, event_data: Dict) -> None:
        """Handle Razorpay webhook events"""
        logger.info(f"Handling Razorpay webhook: {event_type}")
        
        if event_type == "payment.captured":
            # Payment was captured
            payment = event_data["payload"]["payment"]["entity"]
            logger.info(f"Payment captured via webhook: {payment['id']}")
            
        elif event_type == "payment.failed":
            # Payment failed
            payment = event_data["payload"]["payment"]["entity"]
            logger.error(f"Payment failed via webhook: {payment['id']}")
            
            # Update transaction status
            update_query = """
                UPDATE transaction 
                SET status = 'failed', updated = time::now()
                WHERE razorpay_payment_id = $payment_id
            """
            await repo_query(update_query, {"payment_id": payment["id"]})
            
        elif event_type == "refund.processed":
            # Refund was processed
            refund = event_data["payload"]["refund"]["entity"]
            logger.info(f"Refund processed via webhook: {refund['id']}")
            
            # Update refund status
            update_query = """
                UPDATE refund 
                SET status = 'processed', updated = time::now()
                WHERE razorpay_refund_id = $refund_id
            """
            await repo_query(update_query, {"refund_id": refund["id"]})

    # ==================== SUBSCRIPTION PAYMENTS ====================
    
    @staticmethod
    async def create_subscription_payment(
        user_id: str,
        plan_id: str,
        email: str,
        phone: str,
        name: str
    ) -> Dict[str, Any]:
        """Create a payment order for subscription"""
        from api.pricing_service import PricingService
        
        # Get plan details
        plan = await PricingService.get_plan_by_id(plan_id)
        if not plan:
            raise Exception("Plan not found")
        
        # Ensure plan has required attributes
        if not hasattr(plan, 'price') or not hasattr(plan, 'currency') or not hasattr(plan, 'name'):
            logger.error(f"Invalid plan object: {plan}")
            raise Exception(f"Invalid plan data structure")
        
        # Skip customer creation for now - it's optional for orders
        # We'll create customer after successful payment
        logger.info(f"Creating order for user {user_id}, plan {plan_id}")
        
        # Create order directly
        order = await PaymentService.create_order(
            user_id=user_id,
            amount=float(plan.price),
            currency=str(plan.currency),
            description=f"Subscription to {plan.name}",
            metadata={
                "plan_id": plan_id,
                "plan_name": str(plan.name),
                "user_email": email,
                "user_phone": phone,
                "user_name": name
            }
        )
        
        return order
