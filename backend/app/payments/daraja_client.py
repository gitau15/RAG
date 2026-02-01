import requests
import base64
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class DarajaClient:
    """Safaricom Daraja API client for M-Pesa integration"""
    
    def __init__(self):
        self.consumer_key = os.getenv("DARAJA_CONSUMER_KEY", "")
        self.consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET", "")
        self.business_short_code = os.getenv("DARAJA_BUSINESS_SHORT_CODE", "")
        self.passkey = os.getenv("DARAJA_PASSKEY", "")
        self.environment = os.getenv("DARAJA_ENVIRONMENT", "sandbox")  # sandbox or production
        
        # API endpoints
        if self.environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"
            
        self.access_token = None
        self.token_expiry = None
    
    def _get_access_token(self) -> str:
        """Get OAuth access token from Daraja API"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        try:
            credentials = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                # Token expires in 3600 seconds (1 hour)
                self.token_expiry = datetime.now().timestamp() + 3500
                logger.info("Successfully obtained Daraja access token")
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            raise
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK Push"""
        data_to_encode = f"{self.business_short_code}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in YYYYMMDDHHMMSS format"""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def initiate_stk_push(
        self,
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        Initiate M-Pesa STK Push payment
        
        Args:
            phone_number: Customer phone number (format: 2547XXXXXXXX)
            amount: Amount to charge
            account_reference: Account reference for the transaction
            transaction_desc: Transaction description
            callback_url: URL to receive payment confirmation
            
        Returns:
            STK Push response data
        """
        try:
            access_token = self._get_access_token()
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp)
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.business_short_code,
                "PhoneNumber": phone_number,
                "CallBackURL": callback_url or f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/payments/callback",
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"STK Push initiated for {phone_number}: {result.get('ResponseCode')}")
                return {
                    "success": True,
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "response_code": result.get("ResponseCode"),
                    "response_description": result.get("ResponseDescription"),
                    "customer_message": result.get("CustomerMessage")
                }
            else:
                logger.error(f"STK Push failed: {response.text}")
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Error initiating STK Push: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_stk_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Query STK Push payment status
        
        Args:
            checkout_request_id: Checkout request ID from STK Push
            
        Returns:
            Payment status information
        """
        try:
            access_token = self._get_access_token()
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp)
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "result_code": result.get("ResultCode"),
                    "result_desc": result.get("ResultDesc"),
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "response_code": result.get("ResponseCode"),
                    "response_description": result.get("ResponseDescription")
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Error querying STK status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def register_callback_url(
        self,
        validation_url: str,
        confirmation_url: str,
        response_type: str = "Completed"
    ) -> Dict[str, Any]:
        """
        Register callback URLs for payment notifications
        
        Args:
            validation_url: URL for payment validation
            confirmation_url: URL for payment confirmation
            response_type: Response type (Completed or Cancelled)
            
        Returns:
            Registration response
        """
        try:
            access_token = self._get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "ShortCode": self.business_short_code,
                "ResponseType": response_type,
                "ConfirmationURL": confirmation_url,
                "ValidationURL": validation_url
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/c2b/v1/registerurl",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "originator_conversation_id": result.get("OriginatorCoversationID"),
                    "response_code": result.get("ResponseCode"),
                    "response_description": result.get("ResponseDescription")
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Error registering callback URL: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_payment(self, payment_data: Dict[str, Any]) -> bool:
        """
        Validate incoming payment notification
        
        Args:
            payment_data: Payment data from callback
            
        Returns:
            Boolean indicating if payment is valid
        """
        try:
            # Verify required fields exist
            required_fields = ["TransactionType", "TransID", "TransTime", "TransAmount", "BusinessShortCode", "BillRefNumber", "InvoiceNumber", "OrgAccountBalance", "ThirdPartyTransID", "MSISDN", "FirstName", "MiddleName", "LastName"]
            
            for field in required_fields:
                if field not in payment_data:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Verify business short code matches
            if str(payment_data["BusinessShortCode"]) != str(self.business_short_code):
                logger.warning("Business short code mismatch")
                return False
            
            # Verify amount is positive
            if float(payment_data["TransAmount"]) <= 0:
                logger.warning("Invalid transaction amount")
                return False
            
            logger.info(f"Payment validated successfully: {payment_data['TransID']}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating payment: {str(e)}")
            return False

# Global instance
daraja_client = DarajaClient()