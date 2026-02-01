import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.payments.daraja_client import daraja_client
from app.orchestrator.rag_orchestrator import rag_orchestrator

logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentProcessor:
    """Payment processor for M-Pesa transactions"""
    
    def __init__(self):
        self.daraja = daraja_client
        self.pending_payments = {}  # Track pending payments
    
    async def initiate_payment(
        self,
        user_id: str,
        amount: float,
        phone_number: str,
        product_info: Dict[str, Any],
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        Initiate payment for product/service
        
        Args:
            user_id: User identifier
            amount: Payment amount
            phone_number: Customer phone number
            product_info: Product/service information
            collection_name: Associated collection (for document purchases)
            
        Returns:
            Payment initiation response
        """
        try:
            # Format phone number (ensure it starts with 2547)
            formatted_phone = self._format_phone_number(phone_number)
            
            # Generate unique account reference
            account_reference = f"RAG_{user_id}_{int(datetime.now().timestamp())}"
            transaction_desc = f"RAG Platform - {product_info.get('name', 'Service')}"
            
            # Initiate STK Push
            response = self.daraja.initiate_stk_push(
                phone_number=formatted_phone,
                amount=amount,
                account_reference=account_reference,
                transaction_desc=transaction_desc
            )
            
            if response["success"]:
                # Store payment info for tracking
                payment_id = response["checkout_request_id"]
                self.pending_payments[payment_id] = {
                    "user_id": user_id,
                    "amount": amount,
                    "phone_number": formatted_phone,
                    "product_info": product_info,
                    "collection_name": collection_name,
                    "account_reference": account_reference,
                    "status": PaymentStatus.PENDING.value,
                    "created_at": datetime.now().isoformat()
                }
                
                logger.info(f"Payment initiated for user {user_id}: {payment_id}")
                
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "merchant_request_id": response["merchant_request_id"],
                    "customer_message": response["customer_message"],
                    "amount": amount
                }
            else:
                return {
                    "success": False,
                    "error": response["error"]
                }
                
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Check the status of a payment
        
        Args:
            payment_id: Checkout request ID
            
        Returns:
            Payment status information
        """
        try:
            # Query STK status
            response = self.daraja.query_stk_status(payment_id)
            
            if response["success"]:
                # Update local payment status
                if payment_id in self.pending_payments:
                    payment_info = self.pending_payments[payment_id]
                    
                    # Map Daraja result codes to our status
                    result_code = response.get("result_code", "")
                    if result_code == "0":
                        payment_info["status"] = PaymentStatus.COMPLETED.value
                        # Process successful payment
                        await self._process_successful_payment(payment_id)
                    elif result_code in ["1032", "1031"]:  # Cancelled or Timeout
                        payment_info["status"] = PaymentStatus.CANCELLED.value
                    else:
                        payment_info["status"] = PaymentStatus.FAILED.value
                
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "status": self.pending_payments.get(payment_id, {}).get("status", "unknown"),
                    "result_code": response.get("result_code"),
                    "result_desc": response.get("result_desc")
                }
            else:
                return {
                    "success": False,
                    "error": response["error"]
                }
                
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_payment_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment callback from Daraja
        
        Args:
            callback_data: Callback data from M-Pesa
            
        Returns:
            Response for Daraja
        """
        try:
            logger.info(f"Received payment callback: {callback_data}")
            
            # Extract relevant data
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            
            # Find payment in pending payments
            payment_info = None
            for payment_id, info in self.pending_payments.items():
                if info.get("account_reference") == merchant_request_id or payment_id == checkout_request_id:
                    payment_info = info
                    break
            
            if payment_info:
                # Update payment status
                if result_code == 0:  # Success
                    payment_info["status"] = PaymentStatus.COMPLETED.value
                    await self._process_successful_payment(checkout_request_id or merchant_request_id)
                elif result_code == 1032:  # Cancelled
                    payment_info["status"] = PaymentStatus.CANCELLED.value
                else:
                    payment_info["status"] = PaymentStatus.FAILED.value
                
                logger.info(f"Payment {checkout_request_id} status updated to {payment_info['status']}")
            
            # Return success response to Daraja
            return {
                "ResultCode": 0,
                "ResultDesc": "Success"
            }
            
        except Exception as e:
            logger.error(f"Error handling payment callback: {str(e)}")
            return {
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
    
    async def _process_successful_payment(self, payment_id: str):
        """
        Process actions after successful payment
        
        Args:
            payment_id: Payment identifier
        """
        try:
            payment_info = self.pending_payments.get(payment_id)
            if not payment_info:
                return
            
            # Grant access to purchased content
            if payment_info.get("collection_name"):
                await self._grant_collection_access(
                    payment_info["user_id"],
                    payment_info["collection_name"]
                )
            
            # Unlock premium features
            await self._unlock_premium_features(payment_info["user_id"])
            
            # Send confirmation
            await self._send_payment_confirmation(
                payment_info["user_id"],
                payment_info["amount"],
                payment_info["product_info"]
            )
            
            logger.info(f"Successfully processed payment {payment_id} for user {payment_info['user_id']}")
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
    
    async def _grant_collection_access(self, user_id: str, collection_name: str):
        """Grant user access to purchased collection"""
        # Implementation would depend on your user management system
        logger.info(f"Granted access to {collection_name} for user {user_id}")
    
    async def _unlock_premium_features(self, user_id: str):
        """Unlock premium features for user"""
        # Implementation would depend on your feature management system
        logger.info(f"Unlocked premium features for user {user_id}")
    
    async def _send_payment_confirmation(self, user_id: str, amount: float, product_info: Dict[str, Any]):
        """Send payment confirmation to user"""
        # Implementation would depend on your notification system
        logger.info(f"Sent payment confirmation to user {user_id} for KES {amount}")
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number to Daraja required format (2547XXXXXXXX)"""
        # Remove any spaces, dashes, or parentheses
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different input formats
        if clean_number.startswith("0"):
            # Convert 07XX to 2547XX
            return "254" + clean_number[1:]
        elif clean_number.startswith("254"):
            # Already in correct format
            return clean_number
        elif clean_number.startswith("7"):
            # Convert 7XX to 2547XX
            return "254" + clean_number
        else:
            # Assume it's already in correct format
            return clean_number
    
    def get_user_payment_history(self, user_id: str) -> list:
        """Get payment history for a user"""
        history = []
        for payment_id, info in self.pending_payments.items():
            if info.get("user_id") == user_id:
                history.append({
                    "payment_id": payment_id,
                    "amount": info["amount"],
                    "status": info["status"],
                    "product": info["product_info"],
                    "created_at": info["created_at"]
                })
        return history

# Global instance
payment_processor = PaymentProcessor()